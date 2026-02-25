let chartInstance = null;

function generateDrinkUI(delta, isNightMode) {

  const container = document.getElementById("drinkList");
  if (!container) return;

  container.innerHTML = "";

  if (!isNightMode) {
    container.innerHTML =
      "🍃 今夜の飲酒コンディションは15時以降に表示されます";
    return;
  }

  if (!preferredDrinks || preferredDrinks.length === 0) {
    container.innerHTML =
      "設定画面でお酒を選択してください 🍶";
    return;
  }

  const drinkMap = {
    beer: { name: "ビール", icon: "🍺", risk: 3 },
    red_wine: { name: "赤ワイン", icon: "🍷", risk: 5 },
    white_wine: { name: "白ワイン", icon: "🍷", risk: 4 },
    shochu: { name: "焼酎", icon: "🍶", risk: 1 },
    whisky: { name: "ウイスキー", icon: "🥃", risk: 4 },
    sake: { name: "日本酒", icon: "🍶", risk: 2 }
  };

  preferredDrinks.forEach(key => {

    const drink = drinkMap[key];
    if (!drink) return;

    let score = Math.abs(delta) + drink.risk;

    let status = "安心してOK";
    let cls = "safe";

    if (score >= 6) {
      status = "今日は控えよう";
      cls = "danger";
    } else if (score >= 4) {
      status = "少なめに";
      cls = "caution";
    }

    container.innerHTML += `
      <div class="drink-item ${cls}">
        <span class="drink-left">
          <span class="drink-icon">${drink.icon}</span>
          <span class="drink-name">${drink.name}</span>
        </span>
        <span class="drink-status">${status}</span>
      </div>
    `;
  });
}


async function drawPressureChart() {
  try {
    const res = await fetch("/api/pressure");
    const data = await res.json();

<<<<<<< HEAD
    // グラフは display_labels を優先（なければ labels）
const labels = Array.isArray(data.display_labels) ? data.display_labels
             : (Array.isArray(data.labels) ? data.labels : []);

const values = Array.isArray(data.values) ? data.values : [];
=======
    const labels = data.labels;
    const values = data.values;
>>>>>>> MVP-mkmaguro

    if (!labels || !values || labels.length < 2) return;

    document.getElementById("currentText").textContent =
      data.current_hpa?.toFixed(1) ?? "--";

    document.getElementById("currentTimeText").textContent =
      data.current_time ?? "--";

    document.getElementById("riskBadge").textContent =
      data.risk ?? "---";

<<<<<<< HEAD
    // 年を除いて表示する関数
    const shortDate = (s) =>
      (typeof s === "string" && s.length >= 16)
        ? s.slice(5, 16)   // "MM-DD HH:MM"
        : s;

    if (data.danger_window?.start && data.danger_window?.end) {
      const dh = data.danger_window.delta_hpa;

      const dhTxt = dh != null
        ? `（${(dh > 0 ? "+" : "") + Number(dh).toFixed(1)} hPa）`
        : "";

      dangerLine =
        `要注意：${shortDate(data.danger_window.start)} 〜 ${shortDate(data.danger_window.end)} ${dhTxt}`;
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
    const nowIndex = Number.isInteger(data.i_now) ? data.i_now : null;
    const dangerStart = Number.isInteger(data.danger_window?.start_i) ? data.danger_window.start_i : null;
    const dangerEnd = Number.isInteger(data.danger_window?.end_i) ? data.danger_window.end_i : null;
    // 既存グラフがあれば破棄（メモリ対策）
    if (chartInstance) {
      chartInstance.destroy();
    }
=======
    const ctx = document.getElementById("pressureChart").getContext("2d");

    if (chartInstance) chartInstance.destroy();
>>>>>>> MVP-mkmaguro

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
<<<<<<< HEAD

        animation: false, // 🔥 サイズ暴れ防止

        layout: {
          padding: 0
        },

        plugins: {
          legend: {
            display: true
          },

          annotation: {
            annotations: {
              // 🟨 要注意の時間帯：網掛け（帯）
              dangerBox: (dangerStart != null && dangerEnd != null) ? {
                type: "box",
                xMin: dangerStart,
                xMax: dangerEnd,
                xScaleID: "x",
                backgroundColor: "rgba(255, 193, 7, 0.18)",
                borderWidth: 0
              } : undefined,

              // 🔴 現在の位置：縦線
              nowLine: (nowIndex != null) ? {
                type: "line",
                xMin: nowIndex,
                xMax: nowIndex,
                xScaleID: "x",
                borderColor: "rgba(220, 38, 38, 0.9)",
                borderWidth: 2,
                label: {
                  display: true,
                  content: "現在",
                  position: "start"
                }
              } : undefined
            }
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
            type: "category",
            ticks: {
              maxTicksLimit: 6
            }
          }
        }
=======
        animation: false
>>>>>>> MVP-mkmaguro
      }
    });

    // 🔥 グラフ描画後に呼ぶ（ここが重要）
    generateDrinkUI(
      data.danger_window?.delta_hpa ?? 0,
      data.is_night_mode
    );

  } catch (err) {
    console.error("グラフ描画エラー:", err);
  }
}

window.addEventListener("load", drawPressureChart);