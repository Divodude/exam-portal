const fs = require('fs');
let content = fs.readFileSync('e:/Learning/projects/ExamTest/exam.json', 'utf8');
let fixed = false;
for(let i=0; i<100; i++) {
  try {
    JSON.parse(content);
    console.log('Valid JSON now!');
    fs.writeFileSync('e:/Learning/projects/ExamTest/exam.json', content);
    fixed = true;
    break;
  } catch(e) {
    let match = e.message.match(/at position (\d+)/);
    if(match) {
      let pos = parseInt(match[1]);
      // If it's a quote, replace it with a single quote or escaped quote
      // Usually the parser fails AT the quote or right after it.
      if (content[pos] === '"') {
         content = content.substring(0, pos) + "'" + content.substring(pos + 1);
      } else if (content[pos-1] === '"') {
         content = content.substring(0, pos-1) + "'" + content.substring(pos);
      } else {
         // just try to replace the last quote before pos
         let lastQuote = content.lastIndexOf('"', pos);
         if (lastQuote !== -1) {
             content = content.substring(0, lastQuote) + "'" + content.substring(lastQuote + 1);
         } else {
             break;
         }
      }
    } else {
      console.log('Could not parse error: ' + e.message);
      break;
    }
  }
}
if(!fixed) console.log('Could not fix all errors.');
