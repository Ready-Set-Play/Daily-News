/**
 * Cloudflare Worker — Feedback endpoint for Daily Brief thumbs up/down.
 *
 * Deploy with: wrangler deploy
 * Route: https://your-worker.workers.dev/feedback
 *
 * Query params:
 *   id        — article ID (sha256 prefix)
 *   dir       — "up" or "down"
 *   topic     — topic string (ai_coding, technology, etc.)
 *
 * The worker writes the event to a GitHub repository file via the GitHub API.
 * Requires env vars: GITHUB_TOKEN, GITHUB_REPO (owner/repo), GITHUB_BRANCH
 *
 * Endpoints:
 *   GET /feedback?id=...&dir=...&topic=...  — record feedback
 *   GET /health                              — verify GitHub token and config
 */

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/health") {
      return handleHealth(env);
    }

    if (url.pathname !== "/feedback") {
      return new Response("Not found", { status: 404 });
    }

    const id = url.searchParams.get("id") || "";
    const dir = url.searchParams.get("dir") || "";
    const topic = url.searchParams.get("topic") || "";

    // Validate inputs
    if (!id || !["up", "down"].includes(dir)) {
      return redirectToThanks(dir);
    }

    const entry = JSON.stringify({
      id,
      direction: dir,
      topic,
      timestamp: new Date().toISOString(),
      ua: request.headers.get("User-Agent")?.substring(0, 100) || "",
    });

    try {
      await appendToGitHub(entry, env);
    } catch (e) {
      // Full error (including GitHub API response body) logged for Cloudflare dashboard
      console.error("GitHub append failed:", e.message);
    }

    return redirectToThanks(dir);
  },
};

async function handleHealth(env) {
  const checks = {
    github_token_set: !!env.GITHUB_TOKEN,
    github_repo: env.GITHUB_REPO || "(not set)",
    github_branch: env.GITHUB_BRANCH || "main (default)",
    github_api: null,
  };

  if (env.GITHUB_TOKEN && env.GITHUB_REPO) {
    try {
      const resp = await fetch(`https://api.github.com/repos/${env.GITHUB_REPO}`, {
        headers: {
          Authorization: `Bearer ${env.GITHUB_TOKEN}`,
          "User-Agent": "daily-brief-feedback-worker/1.0",
          Accept: "application/vnd.github+json",
        },
      });
      const body = await resp.json();
      checks.github_api = {
        ok: resp.ok,
        status: resp.status,
        repo: resp.ok ? body.full_name : null,
        error: resp.ok ? null : (body.message || `HTTP ${resp.status}`),
      };
    } catch (e) {
      checks.github_api = { ok: false, error: e.message };
    }
  } else {
    checks.github_api = {
      ok: false,
      error: "GITHUB_TOKEN or GITHUB_REPO not configured on worker",
    };
  }

  const allOk = checks.github_token_set && checks.github_api?.ok;

  return new Response(JSON.stringify(checks, null, 2), {
    status: allOk ? 200 : 500,
    headers: { "Content-Type": "application/json" },
  });
}

function redirectToThanks(dir) {
  const emoji = dir === "up" ? "👍" : "👎";
  const html = `<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Thanks!</title>
<style>body{font-family:system-ui;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;background:#f5f5f0}
.box{text-align:center;padding:40px;background:#fff;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,.08)}
h1{font-size:48px;margin:0 0 8px}p{color:#666;font-size:16px}</style></head>
<body><div class="box"><h1>${emoji}</h1><p>Feedback recorded. Thanks!</p>
<p style="font-size:13px;margin-top:16px"><a href="javascript:window.close()" style="color:#999">Close this tab</a></p>
</div></body></html>`;

  return new Response(html, {
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });
}

function githubTokenError(operation) {
  return new Error(
    `GitHub ${operation} failed with 401 Unauthorized. ` +
    `The GITHUB_TOKEN Worker secret has either EXPIRED or been REVOKED/DELETED — ` +
    `GitHub returns the same 401 for both and they cannot be distinguished. ` +
    `Fix: (1) go to github.com/settings/personal-access-tokens, generate a new fine-grained PAT ` +
    `scoped to Ready-Set-Play/Daily-News with Contents read/write permission, ` +
    `(2) update GITHUB_TOKEN in the Cloudflare Worker secrets dashboard, ` +
    `(3) update GITHUB_TOKEN_EXPIRES in GitHub Actions secrets to the new expiry date (YYYY-MM-DD).`
  );
}

async function appendToGitHub(entry, env) {
  const repo = env.GITHUB_REPO;
  const branch = env.GITHUB_BRANCH || "main";
  const path = "feedback/history.jsonl";
  const token = env.GITHUB_TOKEN;

  // Get current file (to get SHA for update)
  const getUrl = `https://api.github.com/repos/${repo}/contents/${path}?ref=${branch}`;
  const getResp = await fetch(getUrl, {
    headers: {
      Authorization: `Bearer ${token}`,
      "User-Agent": "daily-brief-feedback-worker/1.0",
      Accept: "application/vnd.github+json",
    },
  });

  let currentContent = "";
  let sha = null;

  if (getResp.ok) {
    const data = await getResp.json();
    sha = data.sha;
    currentContent = atob(data.content.replace(/\n/g, ""));
  } else if (getResp.status === 401) {
    throw githubTokenError("GET");
  } else if (getResp.status !== 404) {
    const errBody = await getResp.text();
    throw new Error(`GitHub GET failed: ${getResp.status} ${errBody}`);
  }

  // Append new entry
  const newContent = currentContent + entry + "\n";
  const encoded = btoa(unescape(encodeURIComponent(newContent)));

  const body = {
    message: `feedback: ${entry.slice(0, 60)}`,
    content: encoded,
    branch,
    ...(sha ? { sha } : {}),
  };

  const putUrl = `https://api.github.com/repos/${repo}/contents/${path}`;
  const putResp = await fetch(putUrl, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
      "User-Agent": "daily-brief-feedback-worker/1.0",
      Accept: "application/vnd.github+json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (putResp.status === 401) {
    throw githubTokenError("PUT");
  } else if (!putResp.ok) {
    const err = await putResp.text();
    throw new Error(`GitHub PUT failed: ${putResp.status} ${err}`);
  }
}
