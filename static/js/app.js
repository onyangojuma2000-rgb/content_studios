let sourceType = "topic";
let currentPackage = null;

const sourceValue = document.getElementById("sourceValue");
const sourceLabel = document.getElementById("sourceLabel");
const generateBtn = document.getElementById("generateBtn");
const statusBox = document.getElementById("status");

document.querySelectorAll(".toggle-btn").forEach(button => {
  button.addEventListener("click", () => {
    sourceType = button.dataset.source;
    document.querySelectorAll(".toggle-btn").forEach(item => item.classList.toggle("active", item === button));
    sourceLabel.textContent = sourceType === "topic" ? "What should we create content about?" : "Paste the webpage URL";
    sourceValue.placeholder = sourceType === "topic"
      ? "e.g. How Nairobi small businesses can use WhatsApp to improve customer service"
      : "https://example.com/article";
    sourceValue.rows = sourceType === "topic" ? 5 : 2;
  });
});

generateBtn.addEventListener("click", async () => {
  const value = sourceValue.value.trim();
  if (!value) return showStatus("Please enter a topic or URL.", true);

  generateBtn.disabled = true;
  generateBtn.innerHTML = "<span>Creating your content package…</span><span>◌</span>";
  showStatus("Working on your blog post and social content. This can take a little while.");
  try {
    const response = await fetch("/generate", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        source: sourceType,
        value,
        audience: document.getElementById("audience").value.trim(),
        tone: document.getElementById("tone").value
      })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Content generation failed.");
    currentPackage = data.result;
    renderPackage(currentPackage);
    showStatus("Your content package is ready. Review it before publishing.");
  } catch (error) {
    showStatus(error.message || "Unable to generate content. Please try again.", true);
  } finally {
    generateBtn.disabled = false;
    generateBtn.innerHTML = "<span>Generate content package</span><span aria-hidden=\"true\">→</span>";
  }
});

function showStatus(message, isError=false) {
  statusBox.textContent = message;
  statusBox.classList.toggle("error", isError);
}
function renderPackage(data) {
  document.getElementById("emptyState").classList.add("hidden");
  document.getElementById("results").classList.remove("hidden");
  document.getElementById("blogTitle").textContent = data.blog_title;
  document.getElementById("metaDescription").textContent = data.blog_meta_description || "";
  document.getElementById("blogBody").textContent = data.blog_post;
  document.getElementById("tweetsList").replaceChildren();
  data.tweets.forEach((tweet, index) => {
    const card = document.createElement("div");
    card.className = "post-card";
    const number = document.createElement("span");
    number.className = "post-number";
    number.textContent = String(index + 1).padStart(2, "0");
    const content = document.createElement("div");
    content.textContent = tweet;
    card.append(number, content);
    document.getElementById("tweetsList").append(card);
  });
  document.getElementById("linkedinBody").textContent = data.linkedin_post;
  document.getElementById("sourceNote").textContent = data.source_note || "";
  switchTab("blog");
}
function switchTab(name) {
  ["blog", "tweets", "linkedin"].forEach(tab => {
    document.getElementById(tab + "Tab").classList.toggle("hidden", tab !== name);
    document.querySelector(`[data-tab="${tab}"]`).classList.toggle("active", tab === name);
  });
}
document.querySelectorAll(".tab").forEach(button => button.addEventListener("click", () => switchTab(button.dataset.tab)));
document.querySelectorAll(".copy-btn").forEach(button => {
  button.addEventListener("click", async () => {
    if (!currentPackage) return;
    let text = "";
    if (button.dataset.copy === "blog") text = `${currentPackage.blog_title}\n\n${currentPackage.blog_meta_description}\n\n${currentPackage.blog_post}`;
    if (button.dataset.copy === "tweets") text = currentPackage.tweets.map((item, i) => `${i + 1}. ${item}`).join("\n\n");
    if (button.dataset.copy === "linkedin") text = currentPackage.linkedin_post;
    try {
      await navigator.clipboard.writeText(text);
      const old = button.textContent;
      button.textContent = "Copied!";
      setTimeout(() => button.textContent = old, 1400);
    } catch {
      showStatus("Clipboard access was blocked by your browser. Select and copy the text manually.", true);
    }
  });
});
