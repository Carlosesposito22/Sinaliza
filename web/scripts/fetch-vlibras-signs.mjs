// Baixa do dicionário do VLibras os sinais do vocabulário (data/vocabulary.json) para public/vlibras/signs/BR/,
// de onde o front os serve. Rode uma vez (e de novo quando o vocabulário mudar): `npm run signs`.
// Os sinais ficam fora do git: o dicionário do VLibras não traz licença de redistribuição.
import { mkdir, readFile, stat, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const DICTIONARY = "https://dicionario2-dth.vlibras.gov.br/static/BUNDLES/2018.3.1/WEBGL/BR/";
const here = dirname(fileURLToPath(import.meta.url));
const vocabularyPath = join(here, "..", "..", "data", "vocabulary.json");
const outDir = join(here, "..", "public", "vlibras", "signs", "BR");

const vocabulary = JSON.parse(await readFile(vocabularyPath, "utf-8"));
const { split } = JSON.parse(await readFile(join(here, "..", "src", "vlibras-glosses.json"), "utf-8"));
const glosses = vocabulary.signs.map((s) => s.gloss);
const names = [...new Set(glosses.flatMap((g) => split[g] ?? [g.replace(/ /g, "_")]))];

await mkdir(outDir, { recursive: true });
let downloaded = 0;
let existing = 0;
const missing = [];
for (const name of names) {
  const path = join(outDir, name);
  if (await stat(path).then(() => true, () => false)) {
    existing++;
    continue;
  }
  const response = await fetch(DICTIONARY + encodeURIComponent(name));
  if (!response.ok) {
    missing.push(`${name} (${response.status})`);
    continue;
  }
  await writeFile(path, Buffer.from(await response.arrayBuffer()));
  downloaded++;
}
console.log(`${names.length} sinais: ${downloaded} baixados, ${existing} já existiam, ${missing.length} faltando`);
if (missing.length) {
  console.log(`faltando: ${missing.join(", ")}`);
  process.exitCode = 1;
}
