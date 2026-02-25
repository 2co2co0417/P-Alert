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

    const labels = data.labels;
    const values = data.values;

    if (!labels || !values || labels.length < 2) return;

    document.getElementById("currentText").textContent =
      data.current_hpa?.toFixed(1) ?? "--";

    document.getElementById("currentTimeText").textContent =
      data.current_time ?? "--";

    document.getElementById("riskBadge").textContent =
      data.risk ?? "---";

    const ctx = document.getElementById("pressureChart").getContext("2d");

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
        animation: false
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