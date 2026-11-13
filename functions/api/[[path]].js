import jon2Worker from "../../cloudflare/worker.js";

export async function onRequest(context) {
  return jon2Worker.fetch(context.request, context.env);
}
