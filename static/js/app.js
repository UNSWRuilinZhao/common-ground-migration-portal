document.addEventListener("DOMContentLoaded", () => {
    const navToggle = document.querySelector("[data-nav-toggle]");
    const navMenu = document.querySelector("[data-nav-menu]");
    if (navToggle && navMenu) {
        navToggle.addEventListener("click", () => {
            const isOpen = navMenu.classList.toggle("is-open");
            navToggle.setAttribute("aria-expanded", String(isOpen));
            navToggle.setAttribute("aria-label", isOpen ? "Close navigation" : "Open navigation");
        });
        navMenu.querySelectorAll("a").forEach((link) => {
            link.addEventListener("click", () => {
                navMenu.classList.remove("is-open");
                navToggle.setAttribute("aria-expanded", "false");
            });
        });
    }

    document.querySelectorAll('input[type="password"]').forEach((input) => {
        const wrapper = document.createElement("div");
        wrapper.className = "password-wrap";
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);

        const toggle = document.createElement("button");
        toggle.type = "button";
        toggle.className = "password-toggle";
        toggle.setAttribute("aria-label", "Show password");
        toggle.setAttribute("aria-pressed", "false");
        toggle.innerHTML = `
            <svg class="eye-open" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z"></path>
                <circle cx="12" cy="12" r="2.7"></circle>
            </svg>
            <svg class="eye-closed" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M3 3l18 18M10.6 6.2A10.7 10.7 0 0 1 12 6c6 0 9.5 6 9.5 6a16.6 16.6 0 0 1-3 3.6M6.2 6.2C3.8 8 2.5 12 2.5 12s3.5 6 9.5 6c1.2 0 2.3-.2 3.3-.7M9.9 9.9a3 3 0 0 0 4.2 4.2"></path>
            </svg>`;
        wrapper.appendChild(toggle);

        toggle.addEventListener("click", () => {
            const showing = input.type === "text";
            input.type = showing ? "password" : "text";
            toggle.classList.toggle("is-showing", !showing);
            toggle.setAttribute("aria-pressed", String(!showing));
            toggle.setAttribute("aria-label", showing ? "Show password" : "Hide password");
        });
    });

    const loginCard = document.querySelector("[data-login-card]");
    const resetToggle = document.querySelector("[data-reset-toggle]");
    const resetPanel = document.querySelector("[data-reset-panel]");
    const resetClose = document.querySelector("[data-reset-close]");
    const resetRequestForm = document.querySelector("[data-reset-request-form]");
    const resetConfirmForm = document.querySelector("[data-reset-confirm-form]");

    if (loginCard && resetToggle && resetPanel) {
        const resetEmail = resetPanel.querySelector("[data-reset-email]");
        const resetEmailCopy = resetPanel.querySelector("[data-reset-email-copy]");
        const resetCode = resetPanel.querySelector("[data-reset-code]");
        const resetStatus = resetPanel.querySelector("[data-reset-status]");
        const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        const animationDuration = reduceMotion ? 0 : 250;
        let closeTimer;

        resetPanel.inert = true;

        const showStatus = (message, type = "info") => {
            if (!resetStatus) return;
            resetStatus.textContent = message;
            resetStatus.className = `reset-status ${type}`;
            resetStatus.hidden = false;
        };

        const firstErrorMessage = (payload) => {
            if (payload && payload.errors) {
                const messages = Object.values(payload.errors).flat();
                if (messages.length) return messages.join(" ");
            }
            return payload && payload.message
                ? payload.message
                : "Something went wrong. Please try again.";
        };

        const openResetPanel = () => {
            window.clearTimeout(closeTimer);
            resetPanel.hidden = false;
            resetPanel.inert = false;
            resetPanel.setAttribute("aria-hidden", "false");
            resetToggle.setAttribute("aria-expanded", "true");
            loginCard.classList.add("reset-is-open");
            window.requestAnimationFrame(() => resetPanel.classList.add("is-open"));
            window.setTimeout(() => resetEmail && resetEmail.focus(), animationDuration);
        };

        const closeResetPanel = (focusToggle = false) => {
            resetPanel.classList.remove("is-open");
            resetPanel.setAttribute("aria-hidden", "true");
            resetToggle.setAttribute("aria-expanded", "false");
            loginCard.classList.remove("reset-is-open");
            resetPanel.inert = true;
            closeTimer = window.setTimeout(() => {
                if (!resetPanel.classList.contains("is-open")) resetPanel.hidden = true;
            }, animationDuration);
            if (focusToggle) resetToggle.focus();
        };

        resetToggle.addEventListener("click", () => {
            if (resetToggle.getAttribute("aria-expanded") === "true") {
                closeResetPanel();
            } else {
                openResetPanel();
            }
        });

        if (resetClose) {
            resetClose.addEventListener("click", () => closeResetPanel(true));
        }

        resetPanel.addEventListener("keydown", (event) => {
            if (event.key === "Escape") closeResetPanel(true);
        });

        if (resetEmail && resetEmailCopy) {
            const syncResetEmail = () => {
                resetEmailCopy.value = resetEmail.value.trim();
            };
            resetEmail.addEventListener("input", syncResetEmail);
            syncResetEmail();
        }

        if (resetRequestForm) {
            resetRequestForm.addEventListener("submit", async (event) => {
                event.preventDefault();
                if (!resetRequestForm.reportValidity()) return;

                const button = resetRequestForm.querySelector('button[type="submit"]');
                const originalLabel = button.textContent;
                button.disabled = true;
                button.textContent = "Sending…";
                if (resetEmailCopy && resetEmail) resetEmailCopy.value = resetEmail.value.trim();

                try {
                    const response = await fetch(resetRequestForm.action, {
                        method: "POST",
                        body: new FormData(resetRequestForm),
                        credentials: "same-origin",
                        headers: { "X-Requested-With": "XMLHttpRequest" },
                    });
                    const payload = await response.json();
                    if (!response.ok || !payload.ok) throw new Error(firstErrorMessage(payload));
                    showStatus(payload.message, "success");
                    if (resetCode) resetCode.focus();
                } catch (error) {
                    showStatus(error.message || "The code could not be sent. Please try again.", "error");
                } finally {
                    button.disabled = false;
                    button.textContent = originalLabel;
                }
            });
        }

        if (resetConfirmForm) {
            resetConfirmForm.addEventListener("submit", async (event) => {
                event.preventDefault();
                if (!resetConfirmForm.reportValidity()) return;
                if (resetEmailCopy && resetEmail) resetEmailCopy.value = resetEmail.value.trim();

                const button = resetConfirmForm.querySelector('button[type="submit"]');
                const originalLabel = button.textContent;
                button.disabled = true;
                button.textContent = "Resetting…";

                try {
                    const response = await fetch(resetConfirmForm.action, {
                        method: "POST",
                        body: new FormData(resetConfirmForm),
                        credentials: "same-origin",
                        headers: { "X-Requested-With": "XMLHttpRequest" },
                    });
                    const payload = await response.json();
                    if (!response.ok || !payload.ok) throw new Error(firstErrorMessage(payload));
                    showStatus(payload.message, "success");
                    resetConfirmForm.reset();
                    if (resetEmailCopy && resetEmail) resetEmailCopy.value = resetEmail.value.trim();
                } catch (error) {
                    showStatus(error.message || "The password could not be reset. Please try again.", "error");
                } finally {
                    button.disabled = false;
                    button.textContent = originalLabel;
                }
            });
        }
    }

    document.querySelectorAll('[data-date-input="dmy"]').forEach((input) => {
        const form = input.closest("form");
        const field = input.closest(".field");
        const errorMessage =
            "Enter a real date in DD/MM/YYYY format (day 01–31, month 01–12, year 1900–2100).";
        const serverError = field ? field.querySelector(".field-error") : null;
        const error = serverError || document.createElement("div");
        const errorId = `${input.id || input.name}-date-error`;
        error.className = "date-field-error";
        error.id = errorId;
        error.hidden = !serverError;
        error.setAttribute("aria-live", "polite");
        error.innerHTML = `
            <span class="date-error-icon" aria-hidden="true">!</span>
            <span>${errorMessage}</span>`;
        input.insertAdjacentElement("afterend", error);

        const describedBy = input.getAttribute("aria-describedby");
        input.setAttribute(
            "aria-describedby",
            describedBy ? `${describedBy} ${errorId}` : errorId
        );

        const formatDate = (value) => {
            const digits = value.replace(/\D/g, "").slice(0, 8);
            let formatted = digits.slice(0, 2);
            if (digits.length >= 2) formatted += "/";
            if (digits.length > 2) formatted += digits.slice(2, 4);
            if (digits.length >= 4) formatted += "/";
            if (digits.length > 4) formatted += digits.slice(4, 8);
            return formatted;
        };

        const isRealDate = (value) => {
            if (!value) return true;
            const match = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(value);
            if (!match) return false;
            const day = Number(match[1]);
            const month = Number(match[2]);
            const year = Number(match[3]);
            if (year < 1900 || year > 2100) return false;
            const candidate = new Date(Date.UTC(year, month - 1, day));
            return (
                candidate.getUTCFullYear() === year &&
                candidate.getUTCMonth() === month - 1 &&
                candidate.getUTCDate() === day
            );
        };

        let errorHasBeenShown = Boolean(serverError);

        const updateValidity = (showError = errorHasBeenShown) => {
            const isValid = isRealDate(input.value);
            input.setCustomValidity(isValid ? "" : errorMessage);
            const shouldShow = !isValid && showError;
            error.hidden = !shouldShow;
            input.setAttribute("aria-invalid", String(shouldShow));
            if (field) field.classList.toggle("has-date-error", shouldShow);
            if (shouldShow) errorHasBeenShown = true;
            if (isValid) errorHasBeenShown = false;
            return isValid;
        };

        input.addEventListener("input", () => {
            input.value = formatDate(input.value);
            updateValidity(errorHasBeenShown);
        });

        input.addEventListener("keydown", (event) => {
            const cursor = input.selectionStart;
            if (
                event.key !== "Backspace" ||
                cursor === null ||
                cursor !== input.selectionEnd ||
                cursor < 2 ||
                input.value[cursor - 1] !== "/"
            ) {
                return;
            }
            event.preventDefault();
            input.value = `${input.value.slice(0, cursor - 2)}${input.value.slice(cursor)}`;
            input.setSelectionRange(cursor - 2, cursor - 2);
            updateValidity();
        });

        input.addEventListener("blur", () => {
            if (input.value) updateValidity(true);
        });
        updateValidity(errorHasBeenShown);

        if (form) {
            form.addEventListener("submit", (event) => {
                if (!updateValidity(true)) {
                    event.preventDefault();
                    input.focus();
                }
            });
        }
    });
});
