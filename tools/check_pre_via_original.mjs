// Same complete shared-memory corpus, regenerating both CAP and inductance.
process.argv.push('--ported-ind');
await import('./check_shared_heap_original.mjs');
