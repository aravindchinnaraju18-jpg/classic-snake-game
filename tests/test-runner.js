const testVersion = "20260409";
const summaryElement = document.querySelector("#summary");
const resultsElement = document.querySelector("#results");

function formatError(error) {
  if (error instanceof Error) {
    return error.message;
  }

  return String(error);
}

function renderResult({ name, status, detail }) {
  const article = document.createElement("article");
  article.className = `test-result ${status}`;

  const title = document.createElement("strong");
  title.textContent = `${status === "pass" ? "PASS" : "FAIL"}: ${name}`;
  article.appendChild(title);

  if (detail) {
    const message = document.createElement("p");
    message.textContent = detail;
    article.appendChild(message);
  }

  resultsElement.appendChild(article);
}

function toCoverageSummary(snapshot) {
  const functions = Object.entries(snapshot.functions);
  const coveredFunctions = functions.filter(([, count]) => count > 0).length;

  const branches = Object.values(snapshot.branches).flatMap((entry) => [
    entry.true > 0,
    entry.false > 0,
  ]);
  const coveredBranches = branches.filter(Boolean).length;

  const functionCoverage = functions.length
    ? Math.round((coveredFunctions / functions.length) * 100)
    : 100;
  const branchCoverage = branches.length
    ? Math.round((coveredBranches / branches.length) * 100)
    : 100;

  return {
    functionCoverage,
    branchCoverage,
    coveredFunctions,
    totalFunctions: functions.length,
    coveredBranches,
    totalBranches: branches.length,
  };
}

async function run() {
  try {
    const logicModule = await import(`../src/snake-logic.js?v=${testVersion}`);
    const testModule = await import(`./snake-logic.test.js?v=${testVersion}`);
    const { getCoverageSnapshot, resetCoverage } = logicModule;
    const { tests } = testModule;

    resetCoverage();
    let passed = 0;

    for (const test of tests) {
      try {
        test.run();
        passed += 1;
        renderResult({ name: test.name, status: "pass" });
      } catch (error) {
        renderResult({
          name: test.name,
          status: "fail",
          detail: formatError(error),
        });
      }
    }

    const failed = tests.length - passed;
    const coverage = toCoverageSummary(getCoverageSnapshot());
    summaryElement.textContent =
      `${passed}/${tests.length} tests passed${failed ? `, ${failed} failed` : ""}. ` +
      `Function coverage: ${coverage.functionCoverage}% (${coverage.coveredFunctions}/${coverage.totalFunctions}). ` +
      `Branch coverage: ${coverage.branchCoverage}% (${coverage.coveredBranches}/${coverage.totalBranches}).`;
  } catch (error) {
    summaryElement.textContent = "Tests could not start.";
    renderResult({
      name: "Test runner startup",
      status: "fail",
      detail: formatError(error),
    });
  }
}

run();
