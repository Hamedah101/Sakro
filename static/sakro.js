function showToast(message) {
    const toast = document.getElementById("toast");
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add("show");
    setTimeout(() => toast.classList.remove("show"), 2800);
}

function updateClock() {
    const clock = document.getElementById("clock");
    if (!clock) return;
    clock.textContent = new Date().toLocaleString([], {
        weekday: "short",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit"
    });
}

function setupMenu() {
    const sidebar = document.getElementById("sidebar");
    const menuButton = document.getElementById("menuButton");
    if (!sidebar || !menuButton) return;

    menuButton.addEventListener("click", () => {
        sidebar.classList.toggle("open");
    });

    sidebar.querySelectorAll(".nav-item").forEach((item) => {
        item.addEventListener("click", () => {
            sidebar.classList.remove("open");
        });
    });
}

function answerQuestion(text, facts) {
    const q = text.toLowerCase().trim();

    if (!q) {
        return "Type a short question, like “how many threats?”";
    }
    if (q.includes("what is sakro") || q.includes("what does") || q.includes("about")) {
        return "Sakro watches traffic on this computer or lab and shows the packets it saw. It is a learning tool, not a company product.";
    }
    if (q.includes("packet") || q.includes("how many") || q.includes("count")) {
        return "I currently see " + facts.packets + " packet(s) in the traffic file.";
    }
    if (q.includes("threat") || q.includes("danger") || q.includes("attack") || q.includes("suspicious")) {
        return "I found " + facts.threats + " packet(s) that looked unusual. Unusual does not always mean an attack. Open Threats to read each one.";
    }
    if (q.includes("risk")) {
        return "The current risk level is " + facts.risk + ". This is a simple count of unusual packets, not a full security score.";
    }
    if (q.includes("backblaze") || q.includes("blackblaze") || q.includes("cloud") || q.includes("backup") || q.includes("save")) {
        return "You can save a copy of traffic.csv to Backblaze B2 from Settings. That only works in the Python app, not in the plain HTML file.";
    }
    if (q.includes("map") || q.includes("device")) {
        return "Network map lists devices (IP addresses) that showed up in the traffic file.";
    }
    if (q.includes("help") || q.includes("hello") || q.includes("hi")) {
        return "You can ask: how many packets, any threats, what is the risk, or how to save a copy to Backblaze.";
    }
    return "I only know a few questions. Try: “how many packets?”, “any threats?”, “what is the risk?”, or “how do I save to Backblaze?”";
}

function setupBot(facts) {
    const form = document.getElementById("botForm");
    const input = document.getElementById("botInput");
    const log = document.getElementById("chatLog");
    if (!form || !input || !log) return;

    function addBubble(role, message) {
        const bubble = document.createElement("div");
        bubble.className = "chat-bubble " + role;
        bubble.textContent = message;
        log.appendChild(bubble);
        log.scrollTop = log.scrollHeight;
    }

    form.addEventListener("submit", (event) => {
        event.preventDefault();
        const text = input.value.trim();
        if (!text) return;
        addBubble("user", text);
        addBubble("bot", answerQuestion(text, facts));
        input.value = "";
    });

    document.querySelectorAll("[data-ask]").forEach((button) => {
        button.addEventListener("click", () => {
            input.value = button.getAttribute("data-ask");
            form.requestSubmit();
        });
    });
}

function setupDashboard() {
    const scanButton = document.getElementById("scanButton");
    const pauseButton = document.getElementById("pauseButton");
    const streamStatus = document.getElementById("streamStatus");
    const packetCount = document.getElementById("packetCount");
    const dismissAlert = document.getElementById("dismissAlert");
    const threatAlert = document.getElementById("threatAlert");
    let paused = false;
    let packets = packetCount ? parseInt(packetCount.textContent.replace(/,/g, ""), 10) : 0;
    if (Number.isNaN(packets)) packets = 0;

    if (dismissAlert && threatAlert) {
        dismissAlert.addEventListener("click", () => {
            threatAlert.style.display = "none";
        });
    }

    if (scanButton) {
        scanButton.addEventListener("click", () => {
            if (scanButton.classList.contains("scanning")) return;
            scanButton.classList.add("scanning");
            scanButton.textContent = "Scanning…";
            setTimeout(() => {
                scanButton.classList.remove("scanning");
                scanButton.textContent = "Scan done";
                showToast("Scan finished. Refresh the page to reload the traffic file.");
                setTimeout(() => {
                    scanButton.textContent = "Run scan";
                }, 2000);
            }, 1800);
        });
    }

    if (pauseButton && streamStatus) {
        pauseButton.addEventListener("click", () => {
            paused = !paused;
            pauseButton.textContent = paused ? "Resume updates" : "Pause updates";
            streamStatus.textContent = paused ? "Paused" : "Live";
            showToast(paused ? "Updates paused." : "Updates resumed.");
        });
    }

    document.querySelectorAll(".inspect-button").forEach((button) => {
        button.addEventListener("click", () => {
            const row = button.closest("tr");
            if (!row) return;
            showToast(row.cells[0].textContent + " → " + row.cells[1].textContent);
        });
    });

    if (packetCount) {
        setInterval(() => {
            if (!paused) {
                packets += Math.floor(Math.random() * 3);
                packetCount.textContent = packets.toLocaleString();
            }
        }, 2000);
    }
}

function setupStandalonePages() {
    const buttons = document.querySelectorAll("[data-page]");
    if (!buttons.length) return;

    const titles = {
        dashboard: ["Dashboard", "Live view of traffic on your network"],
        map: ["Network map", "Devices that showed up in the traffic list"],
        threats: ["Threats", "Packets that looked unusual"],
        analytics: ["Analytics", "Simple counts and charts"],
        bot: ["Sak bot", "Ask a few questions about this network"],
        settings: ["Settings", "Monitor options and cloud backup"],
        about: ["About", "What Sakro is"]
    };

    function showPage(name) {
        const pageName = titles[name] ? name : "dashboard";
        document.querySelectorAll(".page").forEach((page) => {
            page.classList.toggle("page-hidden", page.id !== "page-" + pageName);
        });
        buttons.forEach((button) => {
            button.classList.toggle("active", button.getAttribute("data-page") === pageName);
        });
        const title = document.getElementById("pageTitle");
        const subtitle = document.getElementById("pageSubtitle");
        if (title) title.textContent = titles[pageName][0];
        if (subtitle) subtitle.textContent = titles[pageName][1];
        const scanButton = document.getElementById("scanButton");
        if (scanButton) {
            scanButton.style.display = "" ;
        }
        if (pageName === "analytics") {
            setupCharts();
        }
        if (location.hash !== "#" + pageName) {
            history.replaceState(null, "", "#" + pageName);
        }
    }

    buttons.forEach((button) => {
        button.addEventListener("click", () => {
            showPage(button.getAttribute("data-page"));
        });
    });

    window.addEventListener("hashchange", () => {
        showPage(location.hash.replace("#", "") || "dashboard");
    });

    showPage(location.hash.replace("#", "") || "dashboard");
}

let chartsReady = false;

function setupCharts() {
    if (chartsReady) return;
    const factsNode = document.getElementById("chartFacts");
    if (!factsNode || !window.Chart) return;

    const facts = JSON.parse(factsNode.textContent);
    const bar = document.getElementById("protocolChart");
    if (bar) {
        new Chart(bar, {
            type: "bar",
            data: {
                labels: Object.keys(facts.protocols || {}),
                datasets: [{
                    label: "Packets",
                    data: Object.values(facts.protocols || {}),
                    backgroundColor: "#58a6ff"
                }]
            },
            options: {
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: "#8b9cb3" }, grid: { color: "#2d3a4d" } },
                    y: { ticks: { color: "#8b9cb3" }, grid: { color: "#2d3a4d" }, beginAtZero: true }
                }
            }
        });
    }

    const pie = document.getElementById("riskChart");
    if (pie) {
        new Chart(pie, {
            type: "doughnut",
            data: {
                labels: ["Looked normal", "Looked unusual"],
                datasets: [{
                    data: [Math.max((facts.total || 0) - (facts.threats || 0), 0), facts.threats || 0],
                    backgroundColor: ["#3fb950", "#f85149"]
                }]
            },
            options: {
                plugins: { legend: { labels: { color: "#e6edf3" } } }
            }
        });
    }
    chartsReady = true;
}

function setupStaticBackblaze() {
    const button = document.getElementById("staticUploadButton");
    if (!button) return;
    button.addEventListener("click", () => {
        showToast("This save-to-cloud button works when you run the Python app (app.py).");
    });
}

document.addEventListener("DOMContentLoaded", () => {
    setupMenu();
    setupDashboard();
    setupStandalonePages();
    setupStaticBackblaze();
    setupCharts();
    updateClock();
    setInterval(updateClock, 1000);

    const factsNode = document.getElementById("networkFacts");
    const facts = factsNode ? JSON.parse(factsNode.textContent) : { packets: 0, threats: 0, risk: "Low" };
    setupBot(facts);
});
