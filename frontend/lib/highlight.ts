export interface Token {
  type: "text" | "comment" | "string" | "keyword";
  value: string;
}

// Single combined-token regex: comments | strings | keywords, matched in one
// pass. Running keyword matching as a *second*, separate pass over HTML that
// an earlier string-highlighting pass already produced would risk matching
// literal text inside that markup (e.g. the word "class" inside a
// class="tok-str" attribute). Tokenizing in one pass over the plain line and
// letting React render the tokens as elements avoids that class of bug
// entirely -- there is no intermediate HTML string to re-scan.
const TOKEN_RE =
  /(#.*$)|("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')|\b(def|class|import|from|return|if|elif|else|for|while|in|not|is|None|True|False|raise|with|as|try|except|finally|pass|continue|break|lambda|and|or|assert)\b/g;

export function tokenizePythonLine(line: string): Token[] {
  const tokens: Token[] = [];
  let lastIndex = 0;
  TOKEN_RE.lastIndex = 0;

  let match: RegExpExecArray | null;
  while ((match = TOKEN_RE.exec(line)) !== null) {
    if (match.index > lastIndex) {
      tokens.push({ type: "text", value: line.slice(lastIndex, match.index) });
    }
    if (match[1] !== undefined) tokens.push({ type: "comment", value: match[1] });
    else if (match[2] !== undefined) tokens.push({ type: "string", value: match[2] });
    else if (match[3] !== undefined) tokens.push({ type: "keyword", value: match[3] });

    lastIndex = TOKEN_RE.lastIndex;
    if (match.index === TOKEN_RE.lastIndex) TOKEN_RE.lastIndex += 1;
  }

  if (lastIndex < line.length) tokens.push({ type: "text", value: line.slice(lastIndex) });
  return tokens;
}
