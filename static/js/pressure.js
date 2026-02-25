let chartInstance = null;

async function drawPressureChart() {
  try {
    const res = await fetch("/api/pressure");
    const data = await res.json();

    // グラフは display_labels を優先（なければ labels）
const labels = Array.isArray(data.display_labels) ? data.display_labels
             : (Array.isArray(data.labels) ? data.labels : []);

const values = Array.isArray(data.values) ? data.values : [];

    const canvas = document.getElementById("pressureChart");
    if (!canvas || labels.length < 2 || values.length < 2) return;

    /* =========================
       画面の数値更新
    ========================== */

    document.getElementById("currentText").textContent =
      data.current_hpa?.toFixed(1) ?? "--";

    document.getElementById("currentTimeText").textContent =
      data.current_time ?? "--";

    // 危険区間表示
    let dangerLine = "要注意：--";

    if (data.danger_window?.start && data.danger_window?.end) {
      const dh = data.danger_window.delta_hpa;

      const dhTxt = dh != null
        ? `（${(dh > 0 ? "+" : "") + Number(dh).toFixed(1)} hPa）`
        : "";

      dangerLine =
        `要注意：${data.danger_window.start} 〜 ${data.danger_window.end} ${dhTxt}`;
    }

    document.getElementById("dangerText").textContent = dangerLine;

    // バッジ更新
    const badge = document.getElementById("riskBadge");
    badge.textContent = data.risk ?? "---";

    if (data.risk === "警戒") {
      badge.style.background = "#ffcdd2";
    } else if (data.risk === "注意") {
      badge.style.background = "#ffe5b4";
    } else {
      badge.style.background = "#c8e6c9";
    }

    /* =========================
       Chart.js グラフ描画
    ========================== */

    const ctx = canvas.getContext("2d");

    // 既存グラフがあれば破棄（メモリ対策）
    if (chartInstance) {
      chartInstance.destroy();
    }

    chartInstance = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: [{
          label: "気圧 (hPa)",
          data: values,
          borderColor: "#2b6cb0",
          borderWidth: 2,
          tension: 0.3,
          pointRadius: 0,
          fill: false
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,

        animation: false, // 🔥 サイズ暴れ防止

        layout: {
          padding: 0
        },

        plugins: {
          legend: {
            display: true
          }
        },

        scales: {
          y: {
            title: {
              display: true,
              text: "hPa"
            }
          },
          x: {
            ticks: {
              maxTicksLimit: 6
            }
          }
        }
      }
    });

  } catch (err) {
    console.error("グラフ描画エラー:", err);
  }
}

window.addEventListener("load", drawPressureChart);