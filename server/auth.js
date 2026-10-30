"use strict";

const crypto = require("crypto");
const { Pool } = require("pg");
const argon2 = require("argon2");
const nodemailer = require("nodemailer");

const pool = process.env.DATABASE_URL
  ? new Pool({
      connectionString: process.env.DATABASE_URL,
      ssl: process.env.PGSSL === "require" ? { rejectUnauthorized: true } : undefined,
      max: 5,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 10000
    })
  : null;

const SESSION_COOKIE = "__Host-jon2_session";
const SESSION_TTL_SECONDS = 60 * 60 * 24 * 7;
const EMAIL_FROM = process.env.EMAIL_FROM || "";
const SMTP_HOST = process.env.SMTP_HOST || "";
const SMTP_PORT = Number(process.env.SMTP_PORT || 587);
const SMTP_USER = process.env.SMTP_USER || "";
const SMTP_PASS = process.env.SMTP_PASS || "";

const dummyPasswordHash = argon2.hash(crypto.randomBytes(32).toString("hex"), { type: argon2.argon2id, memoryCost: 19456, timeCost: 2, parallelism: 1 });

const mailer = SMTP_HOST && SMTP_USER && SMTP_PASS && EMAIL_FROM
  ? nodemailer.createTransport({
      host: SMTP_HOST,
      port: SMTP_PORT,
      secure: SMTP_PORT === 465,
      auth: { user: SMTP_USER, pass: SMTP_PASS },
      connectionTimeout: 10000,
      greetingTimeout: 10000,
      socketTimeout: 15000
    })
  : null;

function configured() {
  return Boolean(pool && mailer);
}

function randomToken() {
  return crypto.randomBytes(32).toString("base64url");
}

function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex");
}

function parseCookies(header = "") {
  const out = Object.create(null);
  for (const part of header.split(";")) {
    const index = part.indexOf("=");
    if (index < 1) continue;
    const key = part.slice(0, index).trim();
    const value = part.slice(index + 1).trim();
    try { out[key] = decodeURIComponent(value); } catch {}
  }
  return out;
}

function cookieOptions() {
  // Cross-origin frontend/API deployments need SameSite=None.
  // Both HTTPS and browser third-party-cookie policy must be considered.
  return "Path=/; HttpOnly; Secure; SameSite=None";
}

function setSessionCookie(res, token) {
  res.setHeader("Set-Cookie", `${SESSION_COOKIE}=${encodeURIComponent(token)}; ${cookieOptions()}; Max-Age=${SESSION_TTL_SECONDS}`);
}

function clearSessionCookie(res) {
  res.setHeader("Set-Cookie", `${SESSION_COOKIE}=; ${cookieOptions()}; Max-Age=0`);
}

function parseSessionToken(req) {
  return parseCookies(req.headers.cookie || "")[SESSION_COOKIE] || "";
}

function validEmail(email) {
  return typeof email === "string" &&
    email.length <= 254 &&
    /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function passwordValid(password) {
  return typeof password === "string" &&
    Buffer.byteLength(password, "utf8") >= 12 &&
    Buffer.byteLength(password, "utf8") <= 128;
}

function publicError(status, message) {
  return Object.assign(new Error(message), { status });
}

async function sendVerification(email, token) {
  const link = `${process.env.JON2_API_PUBLIC_URL || ""}/api/auth/verify?token=${encodeURIComponent(token)}`;
  if (!process.env.JON2_API_PUBLIC_URL) {
    throw new Error("JON2_API_PUBLIC_URL is required to build verification links.");
  }
  await mailer.sendMail({
    from: EMAIL_FROM,
    to: email,
    subject: "تأكيد بريدك الإلكتروني — Jon2 AI",
    text: `مرحبًا بك في Jon2 AI. لتأكيد بريدك الإلكتروني افتح الرابط التالي خلال 24 ساعة:\n\n${link}\n\nإذا لم تنشئ هذا الحساب فتجاهل الرسالة.`,
    html: `<div dir="rtl" style="font-family:Arial,sans-serif;line-height:1.8"><h2>مرحبًا بك في Jon2 AI</h2><p>اضغط الرابط لتأكيد بريدك الإلكتروني. الرابط صالح لمدة 24 ساعة.</p><p><a href="${link}">تأكيد البريد الإلكتروني</a></p><p>إذا لم تنشئ هذا الحساب فتجاهل الرسالة.</p></div>`
  });
}

async function register(emailInput, password) {
  if (!configured()) throw publicError(503, "خدمة التسجيل غير مهيأة بعد. يلزم إعداد قاعدة البيانات والبريد الآمن على الخادم.");
  if (!validEmail(emailInput) || !passwordValid(password)) {
    throw publicError(400, "أدخل بريدًا صحيحًا وكلمة مرور من 12 إلى 128 بايت.");
  }
  const email = emailInput.trim();
  const normalized = email.toLowerCase();
  const passwordHash = await argon2.hash(password, {
    type: argon2.argon2id,
    memoryCost: 19456,
    timeCost: 2,
    parallelism: 1
  });
  const token = randomToken();
  const client = await pool.connect();
  let userId;
  try {
    await client.query("BEGIN");
    const inserted = await client.query(
      `INSERT INTO users (email, email_normalized, password_hash, status)
       VALUES ($1, $2, $3, 'pending')
       ON CONFLICT (email_normalized) DO NOTHING
       RETURNING id`,
      [email, normalized, passwordHash]
    );
    if (!inserted.rowCount) {
      await client.query("ROLLBACK");
      // Avoid disclosing whether an account already exists.
      return { message: "إذا كان البريد صالحًا ومتاحًا، ستصلك رسالة تأكيد." };
    }
    userId = inserted.rows[0].id;
    await client.query(
      `INSERT INTO email_verification_tokens (user_id, token_hash, expires_at)
       VALUES ($1, $2, now() + interval '24 hours')`,
      [userId, sha256(token)]
    );
    await client.query("COMMIT");
  } catch (error) {
    await client.query("ROLLBACK").catch(() => {});
    throw error;
  } finally {
    client.release();
  }

  try {
    await sendVerification(email, token);
  } catch (error) {
    await pool.query("DELETE FROM email_verification_tokens WHERE user_id = $1", [userId]);
    throw publicError(503, "تعذر إرسال رسالة التأكيد الآن. لم يتم تفعيل الحساب؛ حاول لاحقًا.");
  }
  return { message: "تم إنشاء طلب الحساب. افتح رسالة البريد الإلكتروني لتأكيد الحساب." };
}

async function verifyEmail(token) {
  if (!pool) throw publicError(503, "قاعدة البيانات غير مهيأة.");
  if (typeof token !== "string" || token.length < 30 || token.length > 100) {
    throw publicError(400, "رابط التأكيد غير صالح أو منتهي.");
  }
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    const found = await client.query(
      `SELECT id, user_id FROM email_verification_tokens
       WHERE token_hash = $1 AND consumed_at IS NULL AND expires_at > now()
       FOR UPDATE`,
      [sha256(token)]
    );
    if (!found.rowCount) {
      await client.query("ROLLBACK");
      throw publicError(400, "رابط التأكيد غير صالح أو منتهي.");
    }
    const row = found.rows[0];
    await client.query(
      "UPDATE users SET email_verified_at = now(), status = 'active', updated_at = now() WHERE id = $1",
      [row.user_id]
    );
    await client.query(
      "UPDATE email_verification_tokens SET consumed_at = now() WHERE id = $1",
      [row.id]
    );
    await client.query("COMMIT");
    return true;
  } catch (error) {
    await client.query("ROLLBACK").catch(() => {});
    throw error;
  } finally {
    client.release();
  }
}

async function login(emailInput, password, res) {
  if (!pool) throw publicError(503, "قاعدة البيانات غير مهيأة.");
  if (!validEmail(emailInput) || typeof password !== "string" || password.length > 256) {
    throw publicError(401, "البريد الإلكتروني أو كلمة المرور غير صحيحة.");
  }
  const normalized = emailInput.trim().toLowerCase();
  const found = await pool.query(
    "SELECT id, email, password_hash, status, email_verified_at FROM users WHERE email_normalized = $1 LIMIT 1",
    [normalized]
  );
  if (!found.rowCount) {
    const dummyHash = await dummyPasswordHash;
    await argon2.verify(dummyHash, password).catch(() => false);
    throw publicError(401, "البريد الإلكتروني أو كلمة المرور غير صحيحة.");
  }
  const user = found.rows[0];
  const matches = await argon2.verify(user.password_hash, password).catch(() => false);
  if (!matches) throw publicError(401, "البريد الإلكتروني أو كلمة المرور غير صحيحة.");
  if (user.status !== "active" || !user.email_verified_at) {
    throw publicError(403, "أكد بريدك الإلكتروني أولًا قبل تسجيل الدخول.");
  }

  const sessionToken = randomToken();
  const csrfToken = randomToken();
  await pool.query(
    `INSERT INTO user_sessions (user_id, token_hash, csrf_token_hash, expires_at)
     VALUES ($1, $2, $3, now() + interval '7 days')`,
    [user.id, sha256(sessionToken), sha256(csrfToken)]
  );
  setSessionCookie(res, sessionToken);
  return {
    user: { id: user.id, email: user.email },
    csrfToken,
    expiresIn: SESSION_TTL_SECONDS
  };
}

async function currentSession(req) {
  if (!pool) throw publicError(503, "قاعدة البيانات غير مهيأة.");
  const token = parseSessionToken(req);
  if (!token || token.length > 100) return null;
  const result = await pool.query(
    `SELECT s.id AS session_id, s.user_id, s.csrf_token_hash, u.email
     FROM user_sessions s
     JOIN users u ON u.id = s.user_id
     WHERE s.token_hash = $1 AND s.revoked_at IS NULL
       AND s.expires_at > now() AND u.status = 'active'
       AND u.email_verified_at IS NOT NULL
     LIMIT 1`,
    [sha256(token)]
  );
  if (!result.rowCount) return null;
  return result.rows[0];
}

async function rotateCsrf(req) {
  const session = await currentSession(req);
  if (!session) throw publicError(401, "سجّل الدخول أولًا.");
  const csrfToken = randomToken();
  await pool.query(
    "UPDATE user_sessions SET csrf_token_hash = $1, last_seen_at = now() WHERE id = $2",
    [sha256(csrfToken), session.session_id]
  );
  return { user: { id: session.user_id, email: session.email }, csrfToken };
}

async function requireCsrf(req, session) {
  const headerToken = req.headers["x-csrf-token"];
  if (typeof headerToken !== "string" || headerToken.length > 100) {
    throw publicError(403, "تعذر التحقق من الطلب. حدّث الجلسة وحاول مرة أخرى.");
  }
  const expected = Buffer.from(session.csrf_token_hash, "hex");
  const actual = Buffer.from(sha256(headerToken), "hex");
  if (expected.length !== actual.length || !crypto.timingSafeEqual(expected, actual)) {
    throw publicError(403, "تعذر التحقق من الطلب. حدّث الجلسة وحاول مرة أخرى.");
  }
}

async function logout(req, res) {
  const session = await currentSession(req);
  if (session) {
    await requireCsrf(req, session);
    await pool.query(
      "UPDATE user_sessions SET revoked_at = now() WHERE id = $1",
      [session.session_id]
    );
  }
  clearSessionCookie(res);
  return { loggedOut: true };
}

module.exports = {
  configured,
  register,
  verifyEmail,
  login,
  currentSession,
  rotateCsrf,
  requireCsrf,
  logout
};
