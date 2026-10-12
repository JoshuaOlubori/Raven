#!/usr/bin/env node
/**
 * Generate TypeScript types from OpenAPI specification.
 * Run with: npm run generate:api
 */

import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { generate } from 'openapi-typescript';

const OPENAPI_URL = process.env.OPENAPI_URL || 'http://localhost:8000/openapi.json';
const OUTPUT_PATH = resolve(__dirname, '../src/types/api.d.ts');

async function main() {
  console.log(`[generate:api] Fetching OpenAPI spec from ${OPENAPI_URL}...`);

  try {
    const schema = await generate(OPENAPI_URL, {
      // Add any options here
      ignoreErrors: true,
    });

    // Ensure output directory exists
    const dir = resolve(OUTPUT_PATH, '..');
    if (!existsSync(dir)) {
      mkdirSync(dir, { recursive: true });
    }

    writeFileSync(OUTPUT_PATH, schema);
    console.log(`[generate:api] Types written to ${OUTPUT_PATH}`);
  } catch (error) {
    console.error('[generate:api] Failed to generate types:', error);
    process.exit(1);
  }
}

main();
