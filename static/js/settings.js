let currentUser = null;


// ============================================================
// DEFAULT SETTINGS
// ============================================================

const defaultSettings = {
    theme: "system",
    accentColor: "blue",
    compactMode: false,

    showStatistics: true,
    autoRefresh: false,
    refreshInterval: "60",

    defaultTicketView: "all",
    ticketsPerPage: "10",
    showResolved: true,

    notifyAssignment: true,
    notifyStatus: true,
    notifyCritical: true
};


// ============================================================
// LOAD CURRENT USER
// ============================================================
async function loadCurrentUser() {
    try {
        const response = await fetch("/auth/me");

        if (response.status === 401) {
            window.location.href = "/login";
            return;
        }

        if (!response.ok) {
            throw new Error("Unable to load current user");
        }

        const data = await response.json();

        currentUser = data.user;

        displayCurrentUser();

        loadSettings();

    } catch (error) {
        console.error(
            "Error loading current user:",
            error
        );
    }
}


// ============================================================
// DISPLAY ACCOUNT INFORMATION
// ============================================================

function displayCurrentUser() {
    if (!currentUser) {
        return;
    }

    const usersNav =
        document.getElementById("users-nav");

    if (
        usersNav &&
        currentUser.role === "ADMIN"
    ) {
        usersNav.style.display = "block";
    }

    document.getElementById(
        "current-username"
    ).textContent = currentUser.username;

    document.getElementById(
        "current-user-role"
    ).textContent = currentUser.role;

    document.getElementById(
        "current-user-avatar"
    ).textContent =
        currentUser.username
            .charAt(0)
            .toUpperCase();


    document.getElementById(
        "settings-username"
    ).textContent = currentUser.username;

    document.getElementById(
        "settings-email"
    ).textContent = currentUser.email;

    document.getElementById(
        "settings-role"
    ).textContent = currentUser.role;
}


// ============================================================
// LOCAL STORAGE KEY
// ============================================================

function getSettingsStorageKey() {
    if (!currentUser) {
        return "helpdesk-settings";
    }

    return `helpdesk-settings-${currentUser.id}`;
}


// ============================================================
// GET SAVED SETTINGS
// ============================================================

function getSavedSettings() {
    const saved =
        localStorage.getItem(
            getSettingsStorageKey()
        );

    if (!saved) {
        return {
            ...defaultSettings
        };
    }

    try {
        return {
            ...defaultSettings,
            ...JSON.parse(saved)
        };

    } catch (error) {
        console.error(
            "Unable to parse saved settings:",
            error
        );

        return {
            ...defaultSettings
        };
    }
}


// ============================================================
// LOAD SETTINGS INTO FORM
// ============================================================

function loadSettings() {
    const settings = getSavedSettings();


    document.getElementById(
        "theme-setting"
    ).value = settings.theme;


    document.getElementById(
        "accent-color-setting"
    ).value = settings.accentColor;


    document.getElementById(
        "compact-mode-setting"
    ).checked = settings.compactMode;


    document.getElementById(
        "show-statistics-setting"
    ).checked = settings.showStatistics;


    document.getElementById(
        "auto-refresh-setting"
    ).checked = settings.autoRefresh;


    document.getElementById(
        "refresh-interval-setting"
    ).value = settings.refreshInterval;


    document.getElementById(
        "default-ticket-view-setting"
    ).value = settings.defaultTicketView;


    document.getElementById(
        "tickets-per-page-setting"
    ).value = settings.ticketsPerPage;


    document.getElementById(
        "show-resolved-setting"
    ).checked = settings.showResolved;


    document.getElementById(
        "notify-assignment-setting"
    ).checked = settings.notifyAssignment;


    document.getElementById(
        "notify-status-setting"
    ).checked = settings.notifyStatus;


    document.getElementById(
        "notify-critical-setting"
    ).checked = settings.notifyCritical;


    updateRefreshIntervalState();

    applySettings(settings);
}


// ============================================================
// COLLECT SETTINGS FROM PAGE
// ============================================================

function collectSettings() {
    return {

        theme:
            document.getElementById(
                "theme-setting"
            ).value,

        accentColor:
            document.getElementById(
                "accent-color-setting"
            ).value,

        compactMode:
            document.getElementById(
                "compact-mode-setting"
            ).checked,


        showStatistics:
            document.getElementById(
                "show-statistics-setting"
            ).checked,

        autoRefresh:
            document.getElementById(
                "auto-refresh-setting"
            ).checked,

        refreshInterval:
            document.getElementById(
                "refresh-interval-setting"
            ).value,


        defaultTicketView:
            document.getElementById(
                "default-ticket-view-setting"
            ).value,

        ticketsPerPage:
            document.getElementById(
                "tickets-per-page-setting"
            ).value,

        showResolved:
            document.getElementById(
                "show-resolved-setting"
            ).checked,


        notifyAssignment:
            document.getElementById(
                "notify-assignment-setting"
            ).checked,

        notifyStatus:
            document.getElementById(
                "notify-status-setting"
            ).checked,

        notifyCritical:
            document.getElementById(
                "notify-critical-setting"
            ).checked
    };
}


// ============================================================
// SAVE SETTINGS
// ============================================================

function saveSettings() {
    const settings = collectSettings();

    localStorage.setItem(
        getSettingsStorageKey(),
        JSON.stringify(settings)
    );

    applySettings(settings);

    const status =
        document.getElementById(
            "settings-status"
        );

    status.textContent =
        "Settings saved successfully.";

    setTimeout(() => {
        status.textContent =
            "Your preferences are saved.";
    }, 2500);
}


// ============================================================
// APPLY SETTINGS
// ============================================================

function applySettings(settings) {

    applyTheme(settings.theme);

    applyAccentColor(
        settings.accentColor
    );

    document.body.classList.toggle(
        "compact-mode",
        settings.compactMode
    );
}


// ============================================================
// THEME
// ============================================================

function applyTheme(theme) {

    if (theme === "system") {

        const prefersDark =
            window.matchMedia(
                "(prefers-color-scheme: dark)"
            ).matches;

        document.documentElement.dataset.theme =
            prefersDark
                ? "dark"
                : "light";

        return;
    }


    document.documentElement.dataset.theme =
        theme;
}


// ============================================================
// ACCENT COLOR
// ============================================================

function applyAccentColor(color) {

    document.documentElement.dataset.accent =
        color;
}


// ============================================================
// AUTO REFRESH CONTROL
// ============================================================

function updateRefreshIntervalState() {

    const enabled =
        document.getElementById(
            "auto-refresh-setting"
        ).checked;

    const interval =
        document.getElementById(
            "refresh-interval-setting"
        );

    interval.disabled = !enabled;
}


// ============================================================
// MARK SETTINGS AS CHANGED
// ============================================================

function markSettingsChanged() {

    document.getElementById(
        "settings-status"
    ).textContent =
        "You have unsaved changes.";
}


// ============================================================
// CHANGE PASSWORD BUTTON
// ============================================================

function handleChangePassword() {

    document.getElementById(
        "settings-status"
    ).textContent =
        "Password management will be connected to the secure backend endpoint.";
}


// ============================================================
// EVENT LISTENERS
// ============================================================

document
    .getElementById(
        "save-settings-button"
    )
    .addEventListener(
        "click",
        saveSettings
    );


document
    .getElementById(
        "auto-refresh-setting"
    )
    .addEventListener(
        "change",
        () => {
            updateRefreshIntervalState();
            markSettingsChanged();
        }
    );


document
    .getElementById(
        "change-password-button"
    )
    .addEventListener(
        "click",
        handleChangePassword
    );


// ============================================================
// LIVE PREVIEW
// ============================================================

document
    .getElementById(
        "theme-setting"
    )
    .addEventListener(
        "change",
        () => {
            applyTheme(
                document.getElementById(
                    "theme-setting"
                ).value
            );

            markSettingsChanged();
        }
    );


document
    .getElementById(
        "accent-color-setting"
    )
    .addEventListener(
        "change",
        () => {
            applyAccentColor(
                document.getElementById(
                    "accent-color-setting"
                ).value
            );

            markSettingsChanged();
        }
    );


document
    .getElementById(
        "compact-mode-setting"
    )
    .addEventListener(
        "change",
        () => {
            document.body.classList.toggle(
                "compact-mode",
                document.getElementById(
                    "compact-mode-setting"
                ).checked
            );

            markSettingsChanged();
        }
    );


// ============================================================
// WATCH OTHER SETTINGS
// ============================================================

const watchedSettings = [

    "show-statistics-setting",

    "refresh-interval-setting",

    "default-ticket-view-setting",

    "tickets-per-page-setting",

    "show-resolved-setting",

    "notify-assignment-setting",

    "notify-status-setting",

    "notify-critical-setting"
];


watchedSettings.forEach((id) => {

    document
        .getElementById(id)
        .addEventListener(
            "change",
            markSettingsChanged
        );

});


// ============================================================
// PAGE STARTUP
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    async () => {
        await loadCurrentUser();
    }
);
