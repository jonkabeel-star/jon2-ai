// Private Jon2 model cache. IndexedDB stores only the owner's selected bundle.
// Every restore is revalidated by the normal SHA-256 and manifest loader.
const DB_NAME = "jon2-private-model-cache";
const DB_VERSION = 1;
const STORE = "bundles";

function openDatabase() {
  if (!globalThis.indexedDB) return Promise.reject(new Error("IndexedDB is unavailable."));
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE, { keyPath: "key" });
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error || new Error("Could not open Jon2 model cache."));
    request.onblocked = () => reject(new Error("Jon2 model cache upgrade is blocked by another tab."));
  });
}

function transact(mode, operation) {
  return openDatabase().then(db => new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, mode);
    const store = tx.objectStore(STORE);
    let request;
    try { request = operation(store); }
    catch (error) { db.close(); reject(error); return; }
    tx.oncomplete = () => { db.close(); resolve(request?.result); };
    tx.onerror = () => { db.close(); reject(tx.error || new Error("Jon2 model cache transaction failed.")); };
    tx.onabort = () => { db.close(); reject(tx.error || new Error("Jon2 model cache transaction was aborted.")); };
  }));
}

export function jon2CacheKey(checkpointSha256, weightsSha256) {
  return String(checkpointSha256).toLowerCase() + ":" + String(weightsSha256).toLowerCase();
}

export async function saveJon2BundleToCache(checkpointSha256, weightsSha256, manifestBlob, weightsBlob) {
  if (!(manifestBlob instanceof Blob) || !(weightsBlob instanceof Blob)) throw new TypeError("Jon2 cache accepts verified Blob files only.");
  const key = jon2CacheKey(checkpointSha256, weightsSha256);
  await transact("readwrite", store => store.put({
    key, checkpointSha256: checkpointSha256.toLowerCase(),
    weightsSha256: weightsSha256.toLowerCase(),
    manifestBlob, weightsBlob, savedAt: Date.now()
  }));
  return key;
}

export async function getJon2BundleFromCache(checkpointSha256, weightsSha256) {
  const key = jon2CacheKey(checkpointSha256, weightsSha256);
  return (await transact("readonly", store => store.get(key))) || null;
}

export async function getLatestJon2BundleFromCache(checkpointSha256) {
  const records = await transact("readonly", store => store.getAll());
  return (records || [])
    .filter(item => item.checkpointSha256 === String(checkpointSha256).toLowerCase())
    .sort((a, b) => b.savedAt - a.savedAt)[0] || null;
}

export async function deleteJon2BundleFromCache(checkpointSha256, weightsSha256) {
  const key = jon2CacheKey(checkpointSha256, weightsSha256);
  await transact("readwrite", store => store.delete(key));
}

export async function clearJon2BundleCache() {
  await transact("readwrite", store => store.clear());
}
