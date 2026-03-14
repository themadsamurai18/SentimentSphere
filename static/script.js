function postJSON(url, payload) {
    return fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });
}

function startHeartbeat() {
    setInterval(() => {
        fetch("/heartbeat", { method: "POST" }).catch(() => {});
    }, 25000);
}

function setupCharCounter() {
    const textarea = document.getElementById("entry_text");
    const charCount = document.getElementById("charCount");
    if (!textarea || !charCount) {
        return;
    }
    const updateCount = () => {
        charCount.textContent = `${textarea.value.length} characters`;
    };
    textarea.addEventListener("input", updateCount);
    updateCount();
}

function applyTheme(theme) {
    if (!theme) {
        return;
    }
    document.body.setAttribute("data-theme", theme);
}

function refreshCommunityStats() {
    const box = document.getElementById("communityBox");
    if (!box) {
        return;
    }

    const pull = () => {
        fetch("/api/community")
            .then((res) => res.json())
            .then((data) => {
                const set = (id, value) => {
                    const el = document.getElementById(id);
                    if (el) el.textContent = value;
                };
                set("totalMoods", data.total ?? 0);
                set("pctPositive", `${data.positive_pct ?? 0}%`);
                set("pctNeutral", `${data.neutral_pct ?? 0}%`);
                set("pctNegative", `${data.negative_pct ?? 0}%`);
                set("mostCommonEmotion", data.most_common_emotion ?? "No data yet");
            })
            .catch(() => {});
    };

    pull();
    setInterval(pull, 12000);
}

function renderMoodChart() {
    if (!window.MOOD_COUNTS) {
        return;
    }
    const canvas = document.getElementById("moodChart");
    if (!canvas || typeof Chart === "undefined") {
        return;
    }

    const data = window.MOOD_COUNTS;
    new Chart(canvas, {
        type: "line",
        data: {
            labels: ["Positive", "Neutral", "Negative"],
            datasets: [{
                label: "Mood Entries",
                data: [data.Positive, data.Neutral, data.Negative],
                borderColor: "#005f73",
                backgroundColor: "rgba(0,95,115,0.2)",
                fill: true,
                tension: 0.35
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
        }
    });
}

function moodPalette(mood) {
    if (mood === "Positive") {
        return ["#8ecae6", "#ffb703", "#90be6d", "#ffffff"];
    }
    if (mood === "Negative") {
        return ["#023047", "#9b2226", "#6a040f", "#d8d8d8"];
    }
    return ["#219ebc", "#adb5bd", "#8ecae6", "#ffffff"];
}

function renderMoodArt() {
    const canvas = document.getElementById("moodArt");
    if (!canvas) {
        return;
    }

    const themeContainer = document.querySelector("[data-result-theme]");
    if (themeContainer) {
        applyTheme(themeContainer.getAttribute("data-result-theme"));
    }

    const ctx = canvas.getContext("2d");
    const mood = canvas.dataset.mood || "Neutral";
    const polarity = parseFloat(canvas.dataset.polarity || "0");
    const colors = moodPalette(mood);

    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    const base = ctx.createLinearGradient(0, 0, w, h);
    base.addColorStop(0, colors[0]);
    base.addColorStop(0.5, colors[1]);
    base.addColorStop(1, colors[2]);
    ctx.fillStyle = base;
    ctx.fillRect(0, 0, w, h);

    const layers = Math.max(20, Math.min(80, Math.floor((Math.abs(polarity) + 0.2) * 70)));
    for (let i = 0; i < layers; i += 1) {
        const radius = 18 + (i % 12) * 7;
        const x = (Math.sin(i * 1.31 + polarity) * 0.5 + 0.5) * w;
        const y = (Math.cos(i * 1.17 - polarity) * 0.5 + 0.5) * h;
        ctx.beginPath();
        ctx.globalAlpha = 0.13;
        ctx.fillStyle = colors[i % colors.length];
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.fill();
    }

    ctx.globalAlpha = 1;
    ctx.fillStyle = colors[3];
    ctx.font = "700 28px Segoe UI";
    ctx.fillText(`${mood} Energy`, 24, 42);
}

function setupMoodGame() {
    const panel = document.getElementById("gamePanel");
    if (!panel || panel.dataset.gamePage !== "true") {
        return;
    }

    const roundInfo = document.getElementById("roundInfo");
    const emotionPrompt = document.getElementById("emotionPrompt");
    const gameChoices = document.getElementById("gameChoices");
    const gameFeedback = document.getElementById("gameFeedback");
    const gameScore = document.getElementById("gameScore");
    const gameStats = document.getElementById("gameStats");
    const gameComplete = document.getElementById("gameComplete");
    const finalScoreText = document.getElementById("finalScoreText");
    const finalAccuracy = document.getElementById("finalAccuracy");
    const finalSpeed = document.getElementById("finalSpeed");
    const finalTendency = document.getElementById("finalTendency");

    let questions = [];
    let round = 0;
    let score = 0;
    let roundStartedAt = 0;
    let totalReaction = 0;
    const selectedColors = [];

    const tendencyMap = {
        blue: "Calm-oriented",
        green: "Balanced-growth",
        yellow: "Optimistic",
        red: "High-intensity",
        purple: "Reflective-anxious",
        cyan: "Focused-logical",
        pink: "Excited-social",
        gray: "Low-energy",
        "deep blue": "Melancholic",
        orange: "Action-driven",
        maroon: "Pressure-sensitive",
        teal: "Composed"
    };

    function chooseTendency() {
        if (selectedColors.length === 0) {
            return "Balanced";
        }
        const freq = {};
        selectedColors.forEach((c) => {
            freq[c] = (freq[c] || 0) + 1;
        });
        const top = Object.keys(freq).sort((a, b) => freq[b] - freq[a])[0];
        return tendencyMap[top] || "Balanced";
    }

    function finishGame() {
        const total = questions.length || 10;
        const accuracy = total > 0 ? (score / total) * 100 : 0;
        const avgReaction = total > 0 ? totalReaction / total : 0;
        const tendency = chooseTendency();

        panel.classList.add("hidden");
        gameComplete.classList.remove("hidden");

        finalScoreText.textContent = `Score: ${score} / ${total}`;
        finalAccuracy.textContent = `Accuracy: ${accuracy.toFixed(1)}%`;
        finalSpeed.textContent = `Avg reaction speed: ${avgReaction.toFixed(0)} ms`;
        finalTendency.textContent = `Emotional tendency: ${tendency}`;

        postJSON("/game/submit", {
            score,
            total_questions: total,
            accuracy,
            reaction_ms: avgReaction,
            tendency
        }).catch(() => {});
    }

    function renderRound() {
        if (round >= questions.length) {
            finishGame();
            return;
        }

        const q = questions[round];
        roundInfo.textContent = `Round ${round + 1} / ${questions.length}`;
        emotionPrompt.textContent = q.question;
        gameChoices.innerHTML = "";
        gameFeedback.textContent = "";
        gameStats.textContent = "";

        roundStartedAt = performance.now();

        q.options.forEach((choice) => {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "choice-btn";
            btn.textContent = choice;
            btn.addEventListener("click", () => {
                const reaction = performance.now() - roundStartedAt;
                totalReaction += reaction;
                selectedColors.push(choice);

                if (choice === q.correct_color) {
                    score += 1;
                    gameFeedback.textContent = "Correct!";
                } else {
                    gameFeedback.textContent = `Not quite. Correct was ${q.correct_color}.`;
                }

                gameScore.textContent = `Score: ${score}`;
                gameStats.textContent = `Reaction: ${reaction.toFixed(0)} ms`;

                round += 1;
                setTimeout(renderRound, 320);
            });
            gameChoices.appendChild(btn);
        });
    }

    fetch("/game/questions")
        .then((res) => res.json())
        .then((data) => {
            questions = data.questions || [];
            renderRound();
        })
        .catch(() => {
            emotionPrompt.textContent = "Could not load game questions. Refresh page.";
        });
}

function initInsightsCharts() {
    if (!window.INSIGHTS_DATA || typeof Chart === "undefined") {
        return;
    }

    const d = window.INSIGHTS_DATA;

    const distCanvas = document.getElementById("distChart");
    if (distCanvas) {
        new Chart(distCanvas, {
            type: "pie",
            data: {
                labels: ["Positive", "Neutral", "Negative"],
                datasets: [{
                    data: [d.distribution.Positive, d.distribution.Neutral, d.distribution.Negative],
                    backgroundColor: ["#22c55e", "#14b8a6", "#ef4444"]
                }]
            }
        });
    }

    const trendCanvas = document.getElementById("trendChart");
    if (trendCanvas) {
        new Chart(trendCanvas, {
            type: "line",
            data: {
                labels: d.trend.labels,
                datasets: [{
                    label: "Avg Polarity",
                    data: d.trend.values,
                    borderColor: "#0ea5e9",
                    backgroundColor: "rgba(14,165,233,0.2)",
                    fill: true,
                    tension: 0.3
                }]
            }
        });
    }

    const gameCanvas = document.getElementById("gameChart");
    if (gameCanvas) {
        new Chart(gameCanvas, {
            type: "bar",
            data: {
                labels: ["Average Score", "Highest Score", "Games Played"],
                datasets: [{
                    data: [d.game.average, d.game.highest, d.game.played],
                    backgroundColor: ["#3b82f6", "#10b981", "#a855f7"]
                }]
            },
            options: {
                plugins: { legend: { display: false } }
            }
        });
    }

    const radarCanvas = document.getElementById("radarChart");
    if (radarCanvas) {
        new Chart(radarCanvas, {
            type: "radar",
            data: {
                labels: ["Calm", "Stress", "Focus", "Happiness", "Motivation", "Anxiety"],
                datasets: [{
                    label: "Emotional Radar",
                    data: [
                        d.radar.calm,
                        d.radar.stress,
                        d.radar.focus,
                        d.radar.happiness,
                        d.radar.motivation,
                        d.radar.anxiety
                    ],
                    borderColor: "#f97316",
                    backgroundColor: "rgba(249,115,22,0.22)"
                }]
            },
            options: {
                scales: { r: { suggestedMin: 0, suggestedMax: 100 } }
            }
        });
    }
}

document.addEventListener("DOMContentLoaded", () => {
    setupCharCounter();
    renderMoodChart();
    renderMoodArt();
    refreshCommunityStats();
    startHeartbeat();
    setupMoodGame();
    initInsightsCharts();

    const current = document.body.getAttribute("data-theme");
    if (current) {
        applyTheme(current);
    }
});
