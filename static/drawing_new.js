let canvas = document.getElementById("draw-canvas");
let ctx = canvas.getContext("2d");
let bg = document.getElementById("bg-image");

let drawing = false;
let mode = "draw";

bg.onload = function () {
    canvas.width = bg.width;
    canvas.height = bg.height;
};

canvas.addEventListener("mousedown", () => drawing = true);
canvas.addEventListener("mouseup", () => drawing = false);
canvas.addEventListener("mouseout", () => drawing = false);

canvas.addEventListener("mousemove", draw);

function setMode(m) {
    mode = m;
}

function draw(e) {
    if (!drawing) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    ctx.lineWidth = 3;
    ctx.lineCap = "round";

    if (mode === "draw") {
        ctx.strokeStyle = "black";
    } else {
        ctx.strokeStyle = "white";
    }

    ctx.lineTo(x, y);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(x, y);
}

function clearCanvas() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
}

function submitDrawing() {
    let dataURL = canvas.toDataURL("image/png");

    fetch(submitUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image: dataURL })
    }).then(() => {
        alert("Drawing submitted!");
    });
}
