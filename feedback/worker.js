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
 */

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

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

    // Append to GitHub file via API
    try {
      await appendToGitHub(entry, env);
    } catch (e) {
      console.error("GitHub append failed:", e.message);
      // Still show success to user — don't block on backend errors
    }

    return redirectToThanks(dir);
  },
};

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

async function appendToGitHub(entry, env) {
  const repo = env.GITHUB_REPO; // e.g., "timbu/daily-brief"
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
  } else if (getResp.status !== 404) {
    throw new Error(`GitHub GET failed: ${getResp.status}`);
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

  if (!putResp.ok) {
    const err = await putResp.text();
    throw new Error(`GitHub PUT failed: ${putResp.status} ${err}`);
  }
}
