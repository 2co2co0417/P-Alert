let chartInstance = null;

function generateDrinkUI(delta, isNightMode) {
  const container = document.getElementById("drinkList");
  if (!container) return;

  container.innerHTML = "";

  if (!isNightMode) {
    container.innerHTML = "🍃 今夜の飲酒コンディションは15時以降に表示されます";
    return;
  }

  // preferredDrinks はテンプレ側で window.preferredDrinks として渡しておく想定
  const preferred = Array.isArray(window.preferredDrinks) ? window.preferredDrinks : [];
  if (preferred.length === 0) {
    container.innerHTML = "設定画面でお酒を選択してください 🍶";
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

  preferred.forEach((key) => {
    const drink = drinkMap[key];
    if (!drink) return;

    const score = Math.abs(Number(delta) || 0) + drink.risk;

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
    // URLはテンプレから渡すのが安全（なければ /api/pressure）
    const apiUrl = window.PRESSURE_API || "/api/pressure";

    const res = await fetch(apiUrl);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    const data = await res.json();

    // グラフは display_labels を優先（なければ labels）
    const labels = Array.isArray(data.display_labels)
      ? data.display_labels
      : (Array.isArray(data.labels) ? data.labels : []);

    const values = Array.isArray(data.values) ? data.values : [];
    if (labels.length < 2 || values.length < 2) return;

    // 画面反映
    const currentText = document.getElementById("currentText");
    if (currentText) currentText.textContent = (Number(data.current_hpa).toFixed(1) || "--");

    const currentTimeText = document.getElementById("currentTimeText");
    if (currentTimeText) currentTimeText.textContent = data.current_time ?? "--";

    // dangerLine 初期化（未定義防止）
    let dangerLine = "—";

    // 年を除いて表示する関数
    const shortDate = (s) =>
      (typeof s === "string" && s.length >= 16) ? s.slice(5, 16) : s;

    if (data.danger_window?.start && data.danger_window?.end) {
      const dh = data.danger_window.delta_hpa;
      const dhTxt = (dh != null)
        ? `（${(dh > 0 ? "+" : "") + Number(dh).toFixed(1)} hPa）`
        : "";
      dangerLine = `要注意：${shortDate(data.danger_window.start)} 〜 ${shortDate(data.danger_window.end)} ${dhTxt}`;
    }

    const dangerText = document.getElementById("dangerText");
    if (dangerText) dangerText.textContent = dangerLine;

    // バッジ更新
    const badge = document.getElementById("riskBadge");
    if (badge) {
      badge.textContent = data.risk ?? "---";
      if (data.risk === "警戒") {
        badge.style.background = "#ffcdd2";
      } else if (data.risk === "注意") {
        badge.style.background = "#ffe5b4";
      } else {
        badge.style.background = "#c8e6c9";
      }
    }

    /* =========================
       Chart.js グラフ描画
    ========================== */

    // canvas取得（ここが今回の本丸）
    const canvas = document.getElementById("pressureChart");
    if (!canvas) {
      console.error("canvas #pressureChart が見つかりません（index.htmlのid確認）");
      return;
    }
    const ctx = canvas.getContext("2d");

    const nowIndex = Number.isInteger(data.i_now) ? data.i_now : null;
    const dangerStart = Number.isInteger(data.danger_window?.start_i) ? data.danger_window.start_i : null;
    const dangerEnd = Number.isInteger(data.danger_window?.end_i) ? data.danger_window.end_i : null;

    // 既存グラフがあれば破棄（メモリ対策）
    if (chartInstance) chartInstance.destroy();

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
        animation: false, // サイズ暴れ防止
        layout: { padding: 0 },

        plugins: {
          legend: { display: true },
          annotation: {
            annotations: {
              dangerBox: (dangerStart != null && dangerEnd != null) ? {
                type: "box",
                xMin: dangerStart,
                xMax: dangerEnd,
                xScaleID: "x",
                backgroundColor: "rgba(255, 193, 7, 0.18)",
                borderWidth: 0
              } : undefined,

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
          y: { title: { display: true, text: "hPa" } },
          x: { type: "category", ticks: { maxTicksLimit: 6 } }
        }
      }
    });

    // 夜モードフラグ（キー名の揺れに備えてフォールバック）
    const isNightMode = (data.is_night_mode ?? data.isNightMode ?? false);

    // グラフ描画後
    generateDrinkUI(
      data.danger_window?.delta_hpa ?? 0,
      isNightMode
    );

  } catch (err) {
    console.error("グラフ描画エラー:", err);
  }
}

window.addEventListener("load", drawPressureChart);