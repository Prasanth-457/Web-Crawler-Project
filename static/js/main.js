document.addEventListener("DOMContentLoaded", () => {
    const cards = document.querySelectorAll(".page-card, .feature-card, .stat-card");

    cards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.08}s`;
        card.classList.add("reveal");
    });
});