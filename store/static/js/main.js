// console.log("FurniHub loaded successfully!");

document.addEventListener("DOMContentLoaded", function () {

    /* =========================================
       MOBILE MENU
    ========================================= */

    const menuToggle = document.getElementById("menuToggle");
    const mainNav = document.getElementById("mainNav");

    if (menuToggle && mainNav) {

        menuToggle.addEventListener("click", function () {

            mainNav.classList.toggle("active");

            const isOpen = mainNav.classList.contains("active");

            menuToggle.setAttribute(
                "aria-expanded",
                isOpen ? "true" : "false"
            );

        });

    }


    /* =========================================
       ACCOUNT DROPDOWN
    ========================================= */

    const accountMenu = document.querySelector(".account-menu");
    const accountButton = document.querySelector(".account-icon");

    if (accountMenu && accountButton) {

        accountButton.addEventListener("click", function (event) {

            event.stopPropagation();

            accountMenu.classList.toggle("open");

        });


        /* Close account menu when clicking elsewhere */

        document.addEventListener("click", function (event) {

            if (!accountMenu.contains(event.target)) {

                accountMenu.classList.remove("open");

            }

        });

    }


    /* =========================================
       CLOSE MOBILE MENU WHEN LINK IS CLICKED
    ========================================= */

    if (mainNav) {

        const navLinks = mainNav.querySelectorAll("a");

        navLinks.forEach(function (link) {

            link.addEventListener("click", function () {

                if (window.innerWidth <= 700) {

                    mainNav.classList.remove("active");

                    if (menuToggle) {

                        menuToggle.setAttribute(
                            "aria-expanded",
                            "false"
                        );

                    }

                }

            });

        });

    }

});