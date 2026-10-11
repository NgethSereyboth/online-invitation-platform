class LocalRepository {
  read(key, fallback = null) {
    try { return JSON.parse(localStorage.getItem(key)) ?? fallback; }
    catch { return fallback; }
  }
  write(key, value) { localStorage.setItem(key, JSON.stringify(value)); return value; }
  append(key, value) { const items = this.read(key, []); items.push(value); return this.write(key, items); }
  remove(key) { localStorage.removeItem(key); }
}
class IndexedAssetRepository {
  constructor() { this.dbName = 'sovan-invite-assets'; this.storeName = 'assets'; this.memory = new Map(); this.disabled = typeof indexedDB === 'undefined'; }
  open() {
    return new Promise((resolve, reject) => {
      if (this.disabled) return reject(new Error('IndexedDB unavailable'));
      let request;
      try { request = indexedDB.open(this.dbName, 1); }
      catch (error) { this.disabled = true; reject(error); return; }
      request.onupgradeneeded = () => { if (!request.result.objectStoreNames.contains(this.storeName)) request.result.createObjectStore(this.storeName, { keyPath: 'id' }); };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => { this.disabled = true; reject(request.error || new Error('IndexedDB unavailable')); };
      request.onblocked = () => reject(new Error('IndexedDB is blocked'));
    });
  }
  async transaction(mode, action) {
    const db = await this.open();
    return new Promise((resolve, reject) => {
      let tx, request;
      try { tx = db.transaction(this.storeName, mode); request = action(tx.objectStore(this.storeName)); }
      catch (error) { db.close(); reject(error); return; }
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
      tx.oncomplete = () => db.close();
      tx.onerror = () => { db.close(); reject(tx.error || new Error('IndexedDB transaction failed')); };
      tx.onabort = () => { db.close(); reject(tx.error || new Error('IndexedDB transaction aborted')); };
    });
  }
  async put(asset) { let result;try { result=await this.transaction('readwrite',store=>store.put(asset)); } catch { this.memory.set(asset.id,asset);result=asset.id; }window.dispatchEvent?.(new CustomEvent('einvite:assets-changed'));return result; }
  async list() { try { return await this.transaction('readonly', store => store.getAll()); } catch { return [...this.memory.values()]; } }
  async delete(id) { try { await this.transaction('readwrite',store=>store.delete(id)); } catch { this.memory.delete(id); }window.dispatchEvent?.(new CustomEvent('einvite:assets-changed')); }
}
window.inviteStore = new LocalRepository();
window.assetStore = new IndexedAssetRepository();
