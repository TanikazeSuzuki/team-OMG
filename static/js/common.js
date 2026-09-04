const header = document.querySelector(".site-header");
const menuButton = document.querySelector(".menu-button");
const mainNavigation = document.querySelector("#main-navigation");

if (header && menuButton && mainNavigation) {
    const setMenuOpen = (isOpen) => {
        mainNavigation.classList.toggle("is-open", isOpen);
        menuButton.setAttribute("aria-expanded", String(isOpen));
        menuButton.setAttribute(
            "aria-label",
            isOpen ? "メニューを閉じる" : "メニューを開く"
        );
    };

    header.classList.add("navigation-ready");
    setMenuOpen(false);

    menuButton.addEventListener("click", () => {
        setMenuOpen(menuButton.getAttribute("aria-expanded") !== "true");
    });

    mainNavigation.addEventListener("click", (event) => {
        if (event.target.closest("a, button")) {
            setMenuOpen(false);
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            setMenuOpen(false);
            menuButton.focus();
        }
    });

    const desktopQuery = window.matchMedia("(min-width: 769px)");
    desktopQuery.addEventListener("change", (event) => {
        if (event.matches) {
            setMenuOpen(false);
        }
    });
}
