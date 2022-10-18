import { parse } from "node-html-parser";
import lt from "node-languagetool";
import { program } from "commander";
import fs from "fs";
import path from "path";
import throat from "throat";
import changeCase from "change-case";
program.option("-o, --out <path>");
program.parse();
const htmlFilepath = program.args[0];
const options = program.opts();
const outFilepath = options.out;

import { fileURLToPath } from "url";
import { dirname } from "path";
import { formatWithOptions } from "util";
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

console.log("Running!");
lt.start();

if (!htmlFilepath)
  throw Error("First positional argument must be a filepath to an HTML file");
let htmlContent = fs.readFileSync(htmlFilepath, { encoding: "utf-8" });

const lastParagraphFilepath = path.join(__dirname, "last-paragraph.txt");
if (!fs.existsSync(lastParagraphFilepath)) {
  fs.writeFileSync(lastParagraphFilepath, "0");
}
let currentParagraph = Number(fs.readFileSync(lastParagraphFilepath));

const root = parse(htmlContent);
const startInnerHTML = `${root.innerHTML}`;

function writeFinishedHtml() {
  fs.writeFileSync(lastParagraphFilepath, currentParagraph.toString());
  fs.writeFileSync(outFilepath, root.innerHTML);
  // fs.writeFileSync(outFilepath, htmlContent);
}

// Save whatever paragraph we were on last if we hit ctrl-c
let stop = false;
// process.on("SIGINT", () => {
//   stop = true;
//   console.log("\n\nSIGINT!\n");
//   try {
//     writeFinishedHtml();
//   } catch (e) {
//     console.log("\n", e);
//   } finally {
//     process.exit(0);
//   }
// });

const customReplacements = [
  ["CUSTOM_MARKS", "™", ""], // fuck unnecessary marks
  ["CUSTOM_MARKS", "©", ""],
  ["CUSTOM_KIDNAPED", "kidnaped", "kidnapped"],
  ["CUSTOM_TANAKAS", "the Tanaka's", "the Tanakas"],
  ["CUSTOM_TANAKAS", "The Tanaka's", "The Tanakas"],
  ["CUSTOM_WHATELEY", /Whate?le?y/gi, "Whateley"],
  // slurs because it's super distracting to read as-is
  ["CUSTOM_SLUR", /she-?males/gi, "trans women"],
  ["CUSTOM_SLUR", /she-?male/gi, "trans woman"],
  ["CUSTOM_TRANS", "transgendered males", "trans women"],
  ["CUSTOM_TRANS", "transgendered male", "trans woman"],
  ["CUSTOM_TRANS", "transgendered", "transgender"],
  //  ["CUSTOM_TRANS", "TGs", "trans people"],
  //  ["CUSTOM_TRANS", "TG", "trans"],
  //  # typos
  //  ["collage", "college"],
  // weird spelling choices
  ["CUSTOM_SENPAI", "sempai", "senpai"],
  //  style
  ["CUSTOM_ALSO", " also.", "."],
  //  ["©", ""],
  //  # punctuation
  ["CUSTOM_PUNCTUATION", " , ", ", "],
  ["CUSTOM_PUNCTUATION", ",(", ", ("],
  ["CUSTOM_PUNCTUATION", /\. ?\. ?\.? ?/g, "... "],
  ["CUSTOM_PUNCTUATION", " . ", ". "],
  ["CUSTOM_PUNCTUATION", " - ", " — "],
  ["CUSTOM_PUNCTUATION", " -- ", " — "],
  ["CUSTOM_PUNCTUATION", " --- ", " — "],
  //  # one-offs
  ["CUSTOM_ONE_OFF", "grand parents", "grandparents"],
  ["CUSTOM_ONE_OFF", "hard ball", "hardball"],
  ["CUSTOM_ONE_OFF", "the old saw", "the old saying"],
  ["CUSTOM_ONE_OFF", "striaght", "straight"],
  ["CUSTOM_ONE_OFF", "don't'", "don't"],
  ["CUSTOM_ONE_OFF", "just about scarred", "just about scared"],
];

function generateCustomMatches(text) {
  let matches = [];
  for (const [ruleId, pattern, replacement] of customReplacements) {
    if (pattern.constructor.name === "RegExp") {
      const regexMatches = Array.from(text.matchAll(pattern, { global: true }));
      let continueFrom = 0;
      if (regexMatches.length > 0) {
        for (const regexMatch of regexMatches) {
          const offset = regexMatch.index;
          if (offset < continueFrom) continue; // Should avoid overlapping matches
          const original = regexMatch[0];
          const length = original.length;
          continueFrom = offset + length;
          const caseCheckedReplacement = replaceWithCase(original, replacement);
          if (text.slice(offset, offset + length) === caseCheckedReplacement)
            continue; // it applies no change, so ignore it
          matches.push({
            ruleId,
            offset,
            length,
            replacements: [caseCheckedReplacement],
          });
        }
      }
    } else {
      let searchFrom = 0;
      while (text.slice(searchFrom).indexOf(pattern) > -1) {
        // TODO: Maybe do case logic here too
        const index = text.slice(searchFrom).indexOf(pattern);
        matches.push({
          ruleId,
          offset: searchFrom + index,
          length: pattern.length,
          replacements: [replacement],
        });
        searchFrom += index + pattern.length;
      }
    }
  }
  return matches;
}

function replaceWithCase(string, replacement) {
  for (const fn of [
    (s) => s.toUpperCase(),
    (s) => s.toLowerCase(),
    changeCase.sentenceCase,
  ]) {
    if (fn(string) === string) {
      if (string !== fn(replacement))
        console.log(
          `Replacing "${string}" with "${fn(
            replacement,
          )}" (based on "${replacement}")`,
        );
      return fn(replacement);
    }
  }
  return replacement;
}

// Rules I know I want to be applied
const WHITELIST_RULES = [
  "YOUR",
  // "ANY_MORE", // "any more" -> "anymore"
  // "ABOUT_ITS_NN",
  // "IT_IS",
  // "LOT_S",
  // "COMMA_PARENTHESIS_WHITESPACE",
  // "SENTENCE_WHITESPACE",
  // "WHITESPACE_RULE",
  // "FOR_AWHILE",
  // "SENT_START_CONJUNCTIVE_LINKING_ADVERB_COMMA", // Adds commas like "Finally," etc instead when starting a sentence
  // "APOSTROPHE_IN_DATES", // "1920s"
  // "COULD_CARE_LESS",
  // "KNEW_NEW",
  // "WHOS_NN", // who's -> whose
  // "WORST_COMES_TO_WORST",
  // // Rare but valid
  // "AM_LOATHE_TO",
  // // Maybes
  // "ALSO_SENT_END", // replaces " also." with " as well.". I will probably just replace it with nothing instead, lol.
  // "UPPERCASE_SENTENCE_START", // maybe. Messes up on the list starting with "to have no gender". Maybe filter for that case with startsWith('&nbsp;')
  // "KIND_OF_A",
  // "EN_COMPOUNDS", // sure, hyphenate numbers, whatever
  // "VBZ_VBD", // got "is" -> "it" correctly, but may need to be limited to ruleSubId=1
].concat(customReplacements.map(([ruleId]) => ruleId));
const BLACKLIST_RULES = [
  "MORFOLOGIK_RULE_EN_US", // spelling; it doesn't know many common words like "aikido", "dojo", "ki" and slang/affecations like "musta" (must have)
  "ADVERB_WORD_ORDER", // had bad "He'd always been one of" -> "He'd been always one of"
  "WERE_VBB", // misfired on a perfectly fine "were"
  "COMP_THAN", // misfired on "as a real girl" -> "than a real girl"
  "DT_PRP", // "a she" -> "a"
  "NODT_DOZEN", // "dozens, hundreds" -> "dozens, a hundred" instead of "dozens, hundreds"
  "ADJECTIVE_IN_ATTRIBUTE", // "exotic in color" -> "exotic", too style-picky
  "HE_VERB_AGR", // "he father" -> "he fathers" instead of "his father"
  "IT_VBZ", // nonsense, "wore it loose" -> "wore it looses"
  "I_MOVING", // slang, "You planning to ...?"
  "SOME_OF_THE", // "some of the" -> "some". nitpicky style.
  "ENGLISH_WORD_REPEAT_RULE", // "Misfired on "Ta ta!"
  "DT_DT", // double article: trips on "an A student"
  "CD_NN", // trips on "five nine" as a height description
  "MISSING_COMMA_AFTER_INTRODUCTORY_PHRASE", // "Of course, I whatever". Maybe.
  "EVERY_NOW_AND_THEN", // No. Wrong. Stop it.
  "WHO_NOUN", // "Who Dear?" -> "Who is a Dear?"
  "MAY_COULD_POSSIBLY",
  "BEEN_PART_AGREEMENT", // no: "nosed to nose"
  "MUCH_COUNTABLE", // "pretty much" -> "pretty many"
  "EN_QUOTES", // smart quotes
  "TRY_AND",
  "LITTLE_BIT",
  "NOUN_AROUND_IT", // "the woods around them" -> "the surrounding woods"
  "ALL_OF_THE", // "fear at all of the gun" -> "fear at all the gun"
  "WHETHER",
  "MASS_AGREEMENT",
  "DOES_NP_VBZ", // -> "Be she wrong?"
  "PAST_TIME",
  "THE_SUPERLATIVE",
  "AFFECT_EFFECT", // misfires in "But with energy to power his cycle-shoes, he could effect an escape on the ground"
  "DID_BASEFORM", // "Being able to levitate a little as I did helped." -> "...help."
  "NUMEROUS_DIFFERENT",
  "SO_AS_TO",
  "THIS_NNS",
  "AM_I",
  "NO_SPACE_CLOSING_QUOTE", // misfire from ...changed her sheets.  ‘”Bleh!, whatever it was...
  "EN_A_VS_AN", // trips on weird em-dashes:  “I am a mutant, and a -- a -- guh -- girl!
  "NOW", // replaces "no" with "no" at sentence start
  "FELLOW_CLASSMATE",
  "ANY_BODY", // "in any one position for too long" ->
  "TOO_ADJECTIVE_TO", // "from a light black, to Hispanic, to Caucasian" ->
  "THERE_S_MANY",
  "MORE_A_JJ",
  "CONFUSION_OF_OUR_OUT", // got it right the one time, but then wrong later
  "POSSESSIVE_APOSTROPHE", // "girls shower and bathroom" -> girl's or girls'. But messes up "martial arts hall"
];
/* missed typos (very incomplete)
"Finally the spotted a garden store"
ending every sentence with "also"
No period at end of sentence
"the crypt I in habited"
"functioning equipmentis not what..."
"kidnaped" - gets it but with the catch-all spelling rule that I can't use
*/

// console.dir(await check("Does that mean – Is she wrong?", 'en-US'), {depth: 10})
// console.dir(await check("Does that mean — Is she wrong?", 'en-US'), {depth: 10})
// process.exit()

const leaveAlone = [
  "your testing schedule",
  "your plumbing",
  "and your slapping her",
]

const paragraphs = root.querySelectorAll("p");

async function check(text, language) {
  const customMatches = generateCustomMatches(text);
  const ltResult = await lt.check(text, language)
  return { matches: [...customMatches, ...ltResult.matches] };
}

for (const paragraph of paragraphs.slice(
  currentParagraph,
  // currentParagraph + 400,
)) {
  if (stop) break;
  currentParagraph += 1;
  if (paragraph.textContent !== paragraph.innerHTML) {
    // We can't handle this yet
    continue;
  }
  if (paragraph.textContent.length > 1500) {
    // We just choke on these sometimes in a way that doesn't get caught. TODO Split these up into sentences instead
    continue
  }
  const text = paragraph.textContent;
  await check(text, "en-US")
    .then((res) => {
      let fixedText = text;
      let offset = 0;
      let output = "";
      process.stdout.write(`${currentParagraph}/${paragraphs.length}\r`);
      output += `\nParagraph ${currentParagraph}/${paragraphs.length}`;
      let continueFrom = 0;
      for (const match of res.matches) {
        if (match.replacements.length === 0) {
          // console.log(text)
          // console.log(match)
          continue;
        }
        const start = match.offset + offset;
        const end = match.offset + offset + match.length;
        if (start < continueFrom) continue; // Should avoid overlapping matches
        continueFrom = end;
        const origSubstring = fixedText.substring(start, end);
        const replacement = match.replacements[0];
        if (BLACKLIST_RULES.includes(match.ruleId)) {
          // output += `\nIgnoring rule ${match.ruleId}: ${origSubstring} -> ${match.replacements}`;
          continue;
        }

        if (WHITELIST_RULES.includes(match.ruleId)) {
          // output += `\nFollowing rule ${match.ruleId}: ${origSubstring} -> ${replacement}`;
          // continue;
          console.dir(match, null, 2);
          output += `\nReplacing "${origSubstring}" with "${replacement}"`;
          offset += replacement.length - match.length;
          fixedText =
            fixedText.substring(0, start) +
            replacement +
            fixedText.substring(end);
        }
      }
      if (fixedText != text) {
        output += "\n" + text;
        output += "\n" + fixedText;
        const orig = paragraph.textContent;
        paragraph.textContent = fixedText; // maybe use this later instead
      }
      if (output.split("\n").length > 2) console.log(output);

      // htmlContent = htmlContent.replace(text, fixedText);
      // console.log(JSON.stringify(res, null, 2));
    })
    .catch((e) => {
      console.error(e);
    });
  // .finally(() => {
  //   console.log("Done!");
  // });
}

lt.kill();

currentParagraph = 0;
writeFinishedHtml();
