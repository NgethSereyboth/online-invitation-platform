#!/usr/bin/env node
// Reads {key, previous?, samples:[...]} on stdin and prints what the Node
// implementation does with them, so tools/fernet-parity.py can diff against
// the Python module both ways.
import { createFieldCipher } from '../lib/crypto.mjs';

async function readStdin() {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  return JSON.parse(Buffer.concat(chunks).toString('utf8'));
}

const job = await readStdin();
const cipher = createFieldCipher({
  env: {
    EINVITE_FIELD_ENCRYPTION_KEY: job.key,
    EINVITE_FIELD_ENCRYPTION_KEY_PREVIOUS: job.previous ?? '',
  },
  dataDir: undefined,
});

const output = {
  keySource: cipher.keySource,
  revealed: job.samples.map((sample) => cipher.reveal(sample)),
  protected: job.plain.map((value) => cipher.protect(value)),
  rotationFlags: job.samples.map((sample) => cipher.isCurrentKeyCiphertext(sample)),
};
process.stdout.write(JSON.stringify(output));
