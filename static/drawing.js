console.log("Drawing system loaded ✅");

let currentTool = "pencil";
let drawing = false;
let startX, startY;
const history = {};

function setTool(tool) {
    currentTool = tool;
}

/* INIT CANVAS */

function initCanvas(canvas) {

    const img = canvas.parentElement.querySelector(".base-diagram");
    const ctx = canvas.getContext("2d");

    function resizeCanvas() {
        canvas.width = img.clientWidth;
        canvas.height = img.clientHeight;
        canvas.style.width = img.clientWidth + "px";
        canvas.style.height = img.clientHeight + "px";
    }

    if (img.complete) resizeCanvas();
    else img.onload = resizeCanvas;

    history[canvas.id] = { undoStack: [], redoStack: [] };

    saveState(canvas);

    canvas.onmousedown = (e) => {
        drawing = true;
        startX = e.offsetX;
        startY = e.offsetY;
        saveState(canvas);
        ctx.beginPath();
        ctx.moveTo(startX, startY);
    };

    canvas.onmouseup = (e) => {
        if (!drawing) return;
        drawing = false;

        const endX = e.offsetX;
        const endY = e.offsetY;

        ctx.strokeStyle = document.getElementById("colorPicker").value;
        ctx.lineWidth = 2;

        if (currentTool === "line" || currentTool === "ray") {
            ctx.beginPath();
            ctx.moveTo(startX, startY);
            ctx.lineTo(endX, endY);
            ctx.stroke();

            if (currentTool === "ray") {
                drawArrowhead(ctx, startX, startY, endX, endY);
            }
        }

        if (currentTool === "tick") {
            ctx.strokeStyle = "green";
            ctx.beginPath();
            ctx.moveTo(endX - 10, endY);
            ctx.lineTo(endX - 2, endY + 8);
            ctx.lineTo(endX + 12, endY - 10);
            ctx.stroke();
        }

        if (currentTool === "cross") {
            ctx.strokeStyle = "red";
            ctx.beginPath();
            ctx.moveTo(endX - 10, endY - 10);
            ctx.lineTo(endX + 10, endY + 10);
            ctx.moveTo(endX + 10, endY - 10);
            ctx.lineTo(endX - 10, endY + 10);
            ctx.stroke();
        }

        if (currentTool === "underline") {
            ctx.beginPath();
            ctx.moveTo(startX, endY);
            ctx.lineTo(endX, endY);
            ctx.stroke();
        }

        ctx.beginPath();
    };

    canvas.onmousemove = (e) => {
        if (!drawing) return;

        if (currentTool === "pencil") {
            ctx.lineWidth = 2;
            ctx.strokeStyle = document.getElementById("colorPicker").value;
            ctx.lineTo(e.offsetX, e.offsetY);
            ctx.stroke();
        }

        if (currentTool === "eraser") {
            ctx.lineWidth = 12;
            ctx.strokeStyle = "#ffffff";
            ctx.lineTo(e.offsetX, e.offsetY);
            ctx.stroke();
        }

        if (currentTool === "highlight") {
            ctx.lineWidth = 20;
            ctx.strokeStyle = "rgba(255,255,0,0.4)";
            ctx.lineTo(e.offsetX, e.offsetY);
            ctx.stroke();
        }
    };
}

/* Arrow */

function drawArrowhead(ctx, x1, y1, x2, y2) {
    const headLength = 12;
    const angle = Math.atan2(y2 - y1, x2 - x1);

    ctx.beginPath();
    ctx.moveTo(x2, y2);
    ctx.lineTo(x2 - headLength * Math.cos(angle - Math.PI / 6),
               y2 - headLength * Math.sin(angle - Math.PI / 6));

    ctx.moveTo(x2, y2);
    ctx.lineTo(x2 - headLength * Math.cos(angle + Math.PI / 6),
               y2 - headLength * Math.sin(angle + Math.PI / 6));

    ctx.stroke();
}

/* HISTORY */

function saveState(canvas) {
    history[canvas.id].undoStack.push(canvas.toDataURL());
    history[canvas.id].redoStack = [];
}

function restoreState(canvas, dataURL) {
    const ctx = canvas.getContext("2d");
    const img = new Image();

    img.onload = () => {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0);
    };

    img.src = dataURL;
}

function undo(index) {
    const canvas = document.getElementById("teacher_canvas_" + index);
    const stack = history[canvas.id];

    if (!stack || stack.undoStack.length < 2) return;

    stack.redoStack.push(stack.undoStack.pop());
    restoreState(canvas, stack.undoStack[stack.undoStack.length - 1]);
}

function redo(index) {
    const canvas = document.getElementById("teacher_canvas_" + index);
    const stack = history[canvas.id];

    if (!stack || stack.redoStack.length === 0) return;

    const state = stack.redoStack.pop();
    stack.undoStack.push(state);
    restoreState(canvas, state);
}

function clearCanvas(index) {
    const canvas = document.getElementById("teacher_canvas_" + index);
    const ctx = canvas.getContext("2d");

    saveState(canvas);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
}

/* INIT */

window.onload = function () {
    document.querySelectorAll("canvas").forEach(initCanvas);
};
