let currentUser = null;

// ============================================================
// USER SETTINGS
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


function getSettingsStorageKey() {
    if (!currentUser) {
        return "helpdesk-settings";
    }

    return `helpdesk-settings-${currentUser.id}`;
}


function getSavedSettings() {
    const saved = localStorage.getItem(
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
            "Unable to load user settings:",
            error
        );

        return {
            ...defaultSettings
        };
    }
}

function applyStatisticsSetting(showStatistics) {
    const stats = document.querySelector(".stats");

    if (!stats) {
        return;
    }

    stats.style.display = showStatistics ? "" : "none";
}


function applyDashboardSettings(settings) {
    let selectedTheme = settings.theme;

    if (selectedTheme === "system") {
        const prefersDark = window.matchMedia(
            "(prefers-color-scheme: dark)"
        ).matches;

        selectedTheme = prefersDark ? "dark" : "light";
    }

    document.documentElement.dataset.theme = selectedTheme;
    document.documentElement.dataset.accent = settings.accentColor;

    document.body.classList.toggle(
        "compact-mode",
        settings.compactMode
    );

    applyStatisticsSetting(settings.showStatistics);
}


let usersCache = [];
let techniciansCache = [];
let ticketsCache = [];
let currentTicketPage = 1;

let activeSettings = {
    ...defaultSettings
};
let ticketAutoRefreshTimer = null;
/* =========================
   Authentication / User
========================= */

async function loadCurrentUser() {
    try {
        const response = await fetch("/auth/me");

        if (response.status === 401) {
            window.location.href = "/login";
            return false;
        }

        if (!response.ok) {
            throw new Error("Unable to load current user.");
        }

        const data = await response.json();

        currentUser = data.user;

        updateUserInterface();

        return true;

    } catch (error) {
        console.error("Error loading current user:", error);

        window.location.href = "/login";

        return false;
    }
}


function updateUserInterface() {
    if (!currentUser) {
        return;
    }

    const usernameElement = document.getElementById(
        "current-username"
    );

    const roleElement = document.getElementById(
        "current-user-role"
    );

    const avatarElement = document.getElementById(
        "current-user-avatar"
    );

    const usersNav = document.getElementById(
        "users-nav"
    );

    const userManagementSection = document.getElementById(
        "user-management-section"
    );

    if (usernameElement) {
        usernameElement.textContent =
            currentUser.username;
    }

    if (roleElement) {
        roleElement.textContent =
            formatRole(currentUser.role);
    }

    if (avatarElement) {
        avatarElement.textContent =
            getInitials(currentUser.username);
    }

    /*
     * Only administrators can access User Management.
     * Do not hide the section when an administrator's
     * profile information is refreshed.
     */

    if (currentUser.role === "ADMIN") {
        if (usersNav) {
            usersNav.style.display = "";
        }
    } else {
        if (usersNav) {
            usersNav.style.display = "none";
        }

        if (userManagementSection) {
            userManagementSection.style.display =
                "none";
        }
    }
}

function formatRole(role) {
    if (!role) {
        return "";
    }

    return role
        .toLowerCase()
        .replace(/\b\w/g, letter => letter.toUpperCase());
}


function getInitials(username) {
    if (!username) {
        return "?";
    }

    const parts =
        username.trim().split(/\s+/);

    if (parts.length === 1) {
        return parts[0]
            .substring(0, 2)
            .toUpperCase();
    }

    return (
        parts[0][0] +
        parts[parts.length - 1][0]
    ).toUpperCase();
}


/* =========================
   Load Tickets
========================= */

async function loadTickets() {
    try {
        const response =
            await fetch("/tickets");

        if (response.status === 401) {
            window.location.href = "/login";
            return;
        }

        if (!response.ok) {
            throw new Error(
                "Failed to load tickets"
            );
        }

        const tickets =
            await response.json();

	ticketsCache = tickets;

	updateStatistics(ticketsCache);
	renderFilteredTickets();
    } catch (error) {
        console.error(
            "Error loading tickets:",
            error
        );

        const table =
            document.getElementById(
                "tickets-table"
            );

        if (table) {
            table.innerHTML = `
                <tr>
                    <td colspan="5" class="empty">
                        Unable to load tickets.
                    </td>
                </tr>
            `;
        }
    }
}


function configureTicketAutoRefresh(settings) {
    if (ticketAutoRefreshTimer !== null) {
        clearInterval(ticketAutoRefreshTimer);
        ticketAutoRefreshTimer = null;
    }

    if (!settings.autoRefresh) {
        return;
    }

    const refreshIntervalSeconds = Number.parseInt(
        settings.refreshInterval,
        10
    );

    if (
        !Number.isFinite(refreshIntervalSeconds) ||
        refreshIntervalSeconds < 10
    ) {
        console.error(
            "Invalid auto-refresh interval:",
            settings.refreshInterval
        );

        return;
    }

    ticketAutoRefreshTimer = window.setInterval(
        () => {
            loadTickets();
        },
        refreshIntervalSeconds * 1000
    );
}
/* =========================
   Statistics
========================= */

function updateStatistics(tickets) {
    const total =
        tickets.length;

    const open =
        tickets.filter(
            ticket =>
                ticket.status === "OPEN"
        ).length;

    const inProgress =
        tickets.filter(
            ticket =>
                ticket.status === "IN_PROGRESS"
        ).length;

    const critical =
        tickets.filter(
            ticket =>
                ticket.priority === "CRITICAL"
        ).length;

    const totalElement =
        document.getElementById(
            "total-tickets"
        );

    const openElement =
        document.getElementById(
            "open-tickets"
        );

    const progressElement =
        document.getElementById(
            "progress-tickets"
        );

    const criticalElement =
        document.getElementById(
            "critical-tickets"
        );

    if (totalElement) {
        totalElement.textContent =
            total;
    }

    if (openElement) {
        openElement.textContent =
            open;
    }

    if (progressElement) {
        progressElement.textContent =
            inProgress;
    }

    if (criticalElement) {
        criticalElement.textContent =
            critical;
    }
}

function getFilteredTickets() {
    let filteredTickets = [
        ...ticketsCache
    ];

    if (!activeSettings.showResolved) {
        filteredTickets = filteredTickets.filter(
            ticket =>
                ticket.status !== "RESOLVED" &&
                ticket.status !== "CLOSED"
        );
    }

    if (activeSettings.defaultTicketView === "mine") {
        filteredTickets = filteredTickets.filter(
            ticket =>
                String(ticket.created_by?.id) ===
                String(currentUser.id)
        );
    }

    if (activeSettings.defaultTicketView === "assigned") {
        filteredTickets = filteredTickets.filter(
            ticket =>
                String(ticket.assigned_to?.id) ===
                String(currentUser.id)
        );
    }

    return filteredTickets;
}


function renderFilteredTickets() {
    const filteredTickets =
        getFilteredTickets();

    const ticketsPerPage =
        Number.parseInt(
            activeSettings.ticketsPerPage,
            10
        ) || 10;

    const totalPages = Math.max(
        1,
        Math.ceil(
            filteredTickets.length /
            ticketsPerPage
        )
    );

    currentTicketPage = Math.min(
        Math.max(currentTicketPage, 1),
        totalPages
    );

    const startingIndex =
        (currentTicketPage - 1) *
        ticketsPerPage;

    const endingIndex =
        startingIndex +
        ticketsPerPage;

    const visibleTickets =
        filteredTickets.slice(
            startingIndex,
            endingIndex
        );

    renderTickets(visibleTickets);

    updateTicketPagination(
        filteredTickets.length,
        totalPages
    );
}

function updateTicketPagination(
    totalTickets,
    totalPages
) {
    const pagination =
        document.getElementById(
            "ticket-pagination"
        );

    const pageInformation =
        document.getElementById(
            "ticket-page-information"
        );

    const previousButton =
        document.getElementById(
            "previous-page-button"
        );

    const nextButton =
        document.getElementById(
            "next-page-button"
        );

    if (
        !pagination ||
        !pageInformation ||
        !previousButton ||
        !nextButton
    ) {
        return;
    }

    pageInformation.textContent =
        `Page ${currentTicketPage} of ${totalPages} · ` +
        `${totalTickets} ticket${totalTickets === 1 ? "" : "s"}`;

    previousButton.disabled =
        currentTicketPage <= 1;

    nextButton.disabled =
        currentTicketPage >= totalPages;
}


function changeTicketPage(pageChange) {
    const filteredTickets =
        getFilteredTickets();

    const ticketsPerPage =
        Number.parseInt(
            activeSettings.ticketsPerPage,
            10
        ) || 10;

    const totalPages = Math.max(
        1,
        Math.ceil(
            filteredTickets.length /
            ticketsPerPage
        )
    );

    const requestedPage =
        currentTicketPage +
        pageChange;

    if (
        requestedPage < 1 ||
        requestedPage > totalPages
    ) {
        return;
    }

    currentTicketPage =
        requestedPage;

    renderFilteredTickets();
}

/* =========================
   Render Tickets
========================= */
/* =========================
   Render Tickets
========================= */

function renderTickets(tickets) {
    const table =
        document.getElementById(
            "tickets-table"
        );

    if (!table) {
        return;
    }

    if (tickets.length === 0) {

        table.innerHTML = `
            <tr>
                <td colspan="5" class="empty">
                    No tickets found.
                </td>
            </tr>
        `;

        return;
    }

    table.innerHTML =
        tickets.map(ticket => `
            <tr
                class="ticket-row"
                data-ticket-id="${ticket.id}"
            >

                <td>
                    #${ticket.id}
                </td>

                <td>
                    <strong>
                        ${escapeHtml(ticket.title)}
                    </strong>
                </td>

                <td>
                    <span
                        class="badge priority-${ticket.priority.toLowerCase()}"
                    >
                        ${ticket.priority}
                    </span>
                </td>

                <td>
                    <span
                        class="badge status-${ticket.status.toLowerCase()}"
                    >
                        ${ticket.status.replace("_", " ")}
                    </span>
                </td>

                <td>
                    ${escapeHtml(
                        ticket.created_by?.username ||
                        "Unknown"
                    )}
                </td>

            </tr>
        `).join("");
}


/* =========================
   Basic HTML Safety
========================= */

function escapeHtml(value) {
    if (
        value === null ||
        value === undefined
    ) {
        return "";
    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


/* =========================================================
   USER MANAGEMENT
========================================================= */


/* =========================
   Load Users
========================= */

async function loadUsers() {

    if (
        !currentUser ||
        currentUser.role !== "ADMIN"
    ) {
        return;
    }

    const table =
        document.getElementById(
            "users-table"
        );

    if (!table) {
        return;
    }

    try {

        const response =
            await fetch("/admin/users");

        if (response.status === 401) {
            window.location.href = "/login";
            return;
        }

        if (response.status === 403) {
            table.innerHTML = `
                <tr>
                    <td colspan="6" class="empty">
                        You do not have permission to view users.
                    </td>
                </tr>
            `;

            return;
        }

        if (!response.ok) {
            throw new Error(
                "Failed to load users"
            );
        }

        usersCache =
            await response.json();

        techniciansCache =
            usersCache.filter(
                user =>
                    user.role === "TECHNICIAN"
            );

        renderUsers(usersCache);
        populateTechnicianDropdown();

    } catch (error) {

        console.error(
            "Error loading users:",
            error
        );

        table.innerHTML = `
            <tr>
                <td colspan="6" class="empty">
                    Unable to load users.
                </td>
            </tr>
        `;
    }
}


/* =========================
   Render Users
========================= */

function renderUsers(users) {

    const table =
        document.getElementById(
            "users-table"
        );

    if (!table) {
        return;
    }

    if (users.length === 0) {

        table.innerHTML = `
            <tr>
                <td colspan="6" class="empty">
                    No users found.
                </td>
            </tr>
        `;

        return;
    }

    table.innerHTML =
        users.map(user => {

            const isCurrentUser =
                currentUser &&
                user.id === currentUser.id;

            return `
                <tr>

                    <td>
                        #${user.id}
                    </td>

                    <td>
                        <strong>
                            ${escapeHtml(user.username)}
                        </strong>
                    </td>

                    <td>
                        ${escapeHtml(user.email)}
                    </td>

                    <td>
                        <span class="badge role-${user.role.toLowerCase()}">
                            ${formatRole(user.role)}
                        </span>
                    </td>

                    <td>
                        ${formatDate(user.created_at)}
                    </td>

                    <td>

                        <button
                            type="button"
                            class="secondary-btn user-edit-btn"
                            data-user-id="${user.id}"
                        >
                            Edit
                        </button>

                        ${
                            isCurrentUser
                                ? `
                                    <small class="current-user-label">
                                        Your account
                                    </small>
                                  `
                                : ""
                        }

                    </td>

                </tr>
            `;

        }).join("");
}


/* =========================
   Technician Dropdown
========================= */

function populateTechnicianDropdown(
    selectedTechnicianId = ""
) {

    const select =
        document.getElementById(
            "edit-assigned-to"
        );

    if (!select) {
        return;
    }

    select.innerHTML = `
        <option value="">
            Unassigned
        </option>
    `;

    techniciansCache.forEach(
        technician => {

            const option =
                document.createElement(
                    "option"
                );

            option.value =
                technician.id;

            option.textContent =
                `${technician.username} (#${technician.id})`;

            if (
                String(technician.id) ===
                String(selectedTechnicianId)
            ) {
                option.selected = true;
            }

            select.appendChild(option);
        }
    );
}


/* =========================
   Create User Modal
========================= */

const createUserModal =
    document.getElementById(
        "create-user-modal"
    );

const createUserForm =
    document.getElementById(
        "create-user-form"
    );

const createUserError =
    document.getElementById(
        "create-user-error"
    );


function openCreateUserModal() {

    if (!createUserModal) {
        return;
    }

    createUserForm.reset();

    createUserError.textContent = "";

    createUserError.classList.remove(
        "visible"
    );

    createUserModal.classList.add(
        "active"
    );
}


function closeCreateUserModal() {

    if (!createUserModal) {
        return;
    }

    createUserModal.classList.remove(
        "active"
    );

    createUserForm.reset();

    createUserError.textContent = "";

    createUserError.classList.remove(
        "visible"
    );
}


/* =========================
   Create User
========================= */

async function createUser(event) {

    event.preventDefault();

    createUserError.textContent = "";

    createUserError.classList.remove(
        "visible"
    );

    const username =
        document
            .getElementById(
                "create-user-username"
            )
            .value
            .trim();

    const email =
        document
            .getElementById(
                "create-user-email"
            )
            .value
            .trim();

    const password =
        document
            .getElementById(
                "create-user-password"
            )
            .value;

    const role =
        document
            .getElementById(
                "create-user-role"
            )
            .value;

    try {

        const response =
            await fetch(
                "/admin/users",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        username,
                        email,
                        password,
                        role
                    })
                }
            );

        const result =
            await response.json();

        if (response.status === 401) {
            window.location.href =
                "/login";

            return;
        }

        if (response.status === 403) {
            throw new Error(
                "Only administrators can create users."
            );
        }

        if (!response.ok) {
            throw new Error(
                result.error ||
                "Failed to create user."
            );
        }

        closeCreateUserModal();

        await loadUsers();

    } catch (error) {

        console.error(
            "Error creating user:",
            error
        );

        createUserError.textContent =
            error.message;

        createUserError.classList.add(
            "visible"
        );
    }
}


/* =========================================================
   EDIT USER
========================================================= */

const editUserModal =
    document.getElementById(
        "edit-user-modal"
    );

const editUserForm =
    document.getElementById(
        "edit-user-form"
    );

const editUserError =
    document.getElementById(
        "edit-user-error"
    );


let editingUserId = null;


/* =========================
   Open Edit User Modal
========================= */

function openEditUserModal(userId) {

    const user =
        usersCache.find(
            item =>
                item.id === Number(userId)
        );

    if (!user) {
        return;
    }

    editingUserId =
        user.id;

    document.getElementById(
        "edit-user-username"
    ).value =
        user.username;

    document.getElementById(
        "edit-user-email"
    ).value =
        user.email;

    const roleSelect =
        document.getElementById(
            "edit-user-role"
        );

    roleSelect.value =
        user.role;

    const roleHelp =
        document.getElementById(
            "edit-user-role-help"
        );

    /*
       Administrators cannot change
       their own role.
    */

    if (
        currentUser &&
        user.id === currentUser.id
    ) {

        roleSelect.disabled = true;

        roleHelp.textContent =
            "You cannot change your own administrator role.";

    } else {

        roleSelect.disabled = false;

        roleHelp.textContent =
            "Administrators can change user roles.";
    }

    editUserError.textContent = "";

    editUserError.classList.remove(
        "visible"
    );

    editUserModal.classList.add(
        "active"
    );
}


/* =========================
   Close Edit User Modal
========================= */

function closeEditUserModal() {

    editUserModal.classList.remove(
        "active"
    );

    editUserForm.reset();

    editingUserId = null;

    editUserError.textContent = "";

    editUserError.classList.remove(
        "visible"
    );
}


/* =========================
   Submit User Update
========================= */

async function updateUser(event) {

    event.preventDefault();

    if (!editingUserId) {
        return;
    }

    editUserError.textContent = "";

    editUserError.classList.remove(
        "visible"
    );

    const username =
        document
            .getElementById(
                "edit-user-username"
            )
            .value
            .trim();

    const email =
        document
            .getElementById(
                "edit-user-email"
            )
            .value
            .trim();

    const roleSelect =
        document.getElementById(
            "edit-user-role"
        );

    const updatedData = {
        username,
        email
    };

    /*
       Do not send role when editing
       your own account.
    */

    if (
        !(
            currentUser &&
            editingUserId === currentUser.id
        )
    ) {
        updatedData.role =
            roleSelect.value;
    }

    try {

        const response =
            await fetch(
                `/admin/users/${editingUserId}`,
                {
                    method: "PATCH",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            updatedData
                        )
                }
            );

        const result =
            await response.json();

        if (response.status === 401) {
            window.location.href =
                "/login";

            return;
        }

        if (response.status === 403) {
            throw new Error(
                result.error ||
                "You do not have permission to update this user."
            );
        }

        if (!response.ok) {
            throw new Error(
                result.error ||
                "Failed to update user."
            );
        }

        /*
           If the administrator changed
           their own username/email, update
           the top-right profile immediately.
        */

        if (
            currentUser &&
            editingUserId === currentUser.id
        ) {

            currentUser.username =
                result.user.username;

            currentUser.email =
                result.user.email;

            updateUserInterface();
        }

	await loadUsers();

	closeEditUserModal();

	alert(
    	result.message ||
    	    "User updated successfully."
	);
    } catch (error) {

        console.error(
            "Error updating user:",
            error
        );

        editUserError.textContent =
            error.message;

        editUserError.classList.add(
            "visible"
        );
    }
}


/* =========================================================
   USER MANAGEMENT EVENTS
========================================================= */

const createUserButton =
    document.getElementById(
        "create-user-btn"
    );

if (createUserButton) {

    createUserButton.addEventListener(
        "click",
        openCreateUserModal
    );
}


if (createUserForm) {

    createUserForm.addEventListener(
        "submit",
        createUser
    );
}


document
    .getElementById(
        "close-create-user-modal"
    )
    .addEventListener(
        "click",
        closeCreateUserModal
    );


document
    .getElementById(
        "cancel-create-user"
    )
    .addEventListener(
        "click",
        closeCreateUserModal
    );


if (createUserModal) {

    createUserModal.addEventListener(
        "click",
        event => {

            if (
                event.target ===
                createUserModal
            ) {
                closeCreateUserModal();
            }
        }
    );
}


if (editUserForm) {

    editUserForm.addEventListener(
        "submit",
        updateUser
    );
}


document
    .getElementById(
        "close-edit-user-modal"
    )
    .addEventListener(
        "click",
        closeEditUserModal
    );


document
    .getElementById(
        "cancel-edit-user"
    )
    .addEventListener(
        "click",
        closeEditUserModal
    );


if (editUserModal) {

    editUserModal.addEventListener(
        "click",
        event => {

            if (
                event.target ===
                editUserModal
            ) {
                closeEditUserModal();
            }
        }
    );
}


/* =========================
   User Table Actions
========================= */

document
    .getElementById("users-table")
    .addEventListener(
        "click",
        event => {

            const button =
                event.target.closest(
                    ".user-edit-btn"
                );

            if (!button) {
                return;
            }

            const userId =
                button.dataset.userId;

            openEditUserModal(userId);
        }
    );


/* =========================================================
   TICKET DETAILS
========================================================= */

async function openTicketDetails(ticketId) {

    const detailsModal =
        document.getElementById(
            "details-modal"
        );

    try {

        const response =
            await fetch(
                `/tickets/${ticketId}`
            );

        if (response.status === 401) {
            window.location.href =
                "/login";

            return;
        }

        if (response.status === 403) {

            alert(
                "You do not have permission to view this ticket."
            );

            return;
        }

        if (!response.ok) {
            throw new Error(
                "Failed to load ticket"
            );
        }

        const ticket =
            await response.json();

        document.getElementById(
            "details-title"
        ).textContent =
            ticket.title;

        document.getElementById(
            "details-id"
        ).textContent =
            `#${ticket.id}`;

        document.getElementById(
            "details-description"
        ).textContent =
            ticket.description;

        document.getElementById(
            "details-created-by"
        ).textContent =
            ticket.created_by?.username ||
            "Unknown";

        document.getElementById(
            "details-assigned-to"
        ).textContent =
            ticket.assigned_to?.username ||
            "Unassigned";

        document.getElementById(
            "details-created-at"
        ).textContent =
            formatDate(
                ticket.created_at
            );

        document.getElementById(
            "details-updated-at"
        ).textContent =
            formatDate(
                ticket.updated_at
            );

        const priority =
            document.getElementById(
                "details-priority"
            );

        priority.textContent =
            ticket.priority;

        priority.className =
            `badge priority-${ticket.priority.toLowerCase()}`;

        const status =
            document.getElementById(
                "details-status"
            );

        status.textContent =
            ticket.status.replace(
                "_",
                " "
            );

        status.className =
            `badge status-${ticket.status.toLowerCase()}`;

        detailsModal.dataset.ticketId =
            ticket.id;

        updateTicketActionButtons(
            ticket
        );

        detailsModal.classList.add(
            "active"
        );

    } catch (error) {

        console.error(
            "Error loading ticket:",
            error
        );

        alert(
            "Unable to load ticket details."
        );
    }
}


/* =========================
   Ticket Action Permissions
========================= */

function updateTicketActionButtons(
    ticket
) {

    const editButton =
        document.getElementById(
            "edit-ticket-btn"
        );

    const deleteButton =
        document.getElementById(
            "delete-ticket-btn"
        );

    if (!currentUser) {
        return;
    }

    let canEdit = false;

    if (
        currentUser.role === "ADMIN"
    ) {
        canEdit = true;
    }

    else if (
        currentUser.role ===
        "TECHNICIAN" &&
        ticket.assigned_to?.id ===
        currentUser.id
    ) {
        canEdit = true;
    }

    else if (
        currentUser.role === "USER" &&
        ticket.created_by?.id ===
        currentUser.id
    ) {
        canEdit = true;
    }

    editButton.style.display =
        canEdit ? "" : "none";

    deleteButton.style.display =
        currentUser.role === "ADMIN"
            ? ""
            : "none";
}


/* =========================
   Format Date
========================= */

function formatDate(dateString) {

    if (!dateString) {
        return "N/A";
    }

    return new Date(
        dateString
    ).toLocaleString();
}


/* =========================
   Ticket Row Click
========================= */

document
    .getElementById("tickets-table")
    .addEventListener(
        "click",
        event => {

            const row =
                event.target.closest(
                    ".ticket-row"
                );

            if (!row) {
                return;
            }

            const ticketId =
                row.dataset.ticketId;

            openTicketDetails(
                ticketId
            );
        }
    );


/* =========================
   Details Modal
========================= */

document
    .getElementById(
        "close-details-modal"
    )
    .addEventListener(
        "click",
        () => {

            document
                .getElementById(
                    "details-modal"
                )
                .classList.remove(
                    "active"
                );
        }
    );


document
    .getElementById(
        "details-modal"
    )
    .addEventListener(
        "click",
        event => {

            if (
                event.target.id ===
                "details-modal"
            ) {
                event.target.classList.remove(
                    "active"
                );
            }
        }
    );


/* =========================================================
   NEW TICKET MODAL
========================================================= */

const modal =
    document.getElementById(
        "ticket-modal"
    );

const newTicketButton =
    document.getElementById(
        "new-ticket-btn"
    );

const closeModalButton =
    document.getElementById(
        "close-modal"
    );

const cancelTicketButton =
    document.getElementById(
        "cancel-ticket"
    );

const ticketForm =
    document.getElementById(
        "ticket-form"
    );

const formError =
    document.getElementById(
        "form-error"
    );


function openTicketModal() {

    modal.classList.add(
        "active"
    );
}


function closeTicketModal() {

    modal.classList.remove(
        "active"
    );

    ticketForm.reset();

    formError.textContent = "";

    formError.classList.remove(
        "visible"
    );
}


newTicketButton.addEventListener(
    "click",
    openTicketModal
);


closeModalButton.addEventListener(
    "click",
    closeTicketModal
);


cancelTicketButton.addEventListener(
    "click",
    closeTicketModal
);


modal.addEventListener(
    "click",
    event => {

        if (
            event.target === modal
        ) {
            closeTicketModal();
        }
    }
);


/* =========================
   Create Ticket
========================= */

ticketForm.addEventListener(
    "submit",
    async event => {

        event.preventDefault();

        formError.textContent = "";

        formError.classList.remove(
            "visible"
        );

        const ticketData = {

            title:
                document
                    .getElementById(
                        "ticket-title"
                    )
                    .value
                    .trim(),

            description:
                document
                    .getElementById(
                        "ticket-description"
                    )
                    .value
                    .trim(),

            priority:
                document
                    .getElementById(
                        "ticket-priority"
                    )
                    .value
        };

        try {

            const response =
                await fetch(
                    "/tickets",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body:
                            JSON.stringify(
                                ticketData
                            )
                    }
                );

            const result =
                await response.json();

            if (
                response.status === 401
            ) {
                window.location.href =
                    "/login";

                return;
            }

            if (!response.ok) {

                throw new Error(
                    result.error ||
                    "Failed to create ticket"
                );
            }

            closeTicketModal();

            await loadTickets();

        } catch (error) {

            console.error(
                "Error creating ticket:",
                error
            );

            formError.textContent =
                error.message;

            formError.classList.add(
                "visible"
            );
        }
    }
);


/* =========================================================
   EDIT TICKET
========================================================= */

const editModal =
    document.getElementById(
        "edit-modal"
    );

const editForm =
    document.getElementById(
        "edit-ticket-form"
    );

const editError =
    document.getElementById(
        "edit-form-error"
    );


document
    .getElementById(
        "edit-ticket-btn"
    )
    .addEventListener(
        "click",
        async () => {

            const detailsModal =
                document.getElementById(
                    "details-modal"
                );

            const ticketId =
                detailsModal.dataset.ticketId;

            try {

                const response =
                    await fetch(
                        `/tickets/${ticketId}`
                    );

                if (
                    response.status === 401
                ) {
                    window.location.href =
                        "/login";

                    return;
                }

                if (!response.ok) {
                    throw new Error(
                        "Failed to load ticket"
                    );
                }

                const ticket =
                    await response.json();

                document.getElementById(
                    "edit-title"
                ).value =
                    ticket.title;

                document.getElementById(
                    "edit-description"
                ).value =
                    ticket.description;

                document.getElementById(
                    "edit-priority"
                ).value =
                    ticket.priority;

                document.getElementById(
                    "edit-status"
                ).value =
                    ticket.status;

                /*
                   Populate technician dropdown.

                   This replaces the old manual
                   technician ID input.
                */

                if (
                    currentUser.role === "ADMIN"
                ) {

                    if (
                        techniciansCache.length === 0
                    ) {
                        await loadUsers();
                    }

                    populateTechnicianDropdown(
                        ticket.assigned_to?.id || ""
                    );

                } else {

                    populateTechnicianDropdown();
                }

                updateEditFieldPermissions();

                editModal.dataset.ticketId =
                    ticket.id;

                detailsModal.classList.remove(
                    "active"
                );

                editModal.classList.add(
                    "active"
                );

            } catch (error) {

                console.error(error);

                alert(
                    "Unable to load ticket for editing."
                );
            }
        }
    );


function updateEditFieldPermissions() {

    const priorityGroup =
        document
            .getElementById(
                "edit-priority"
            )
            .closest(".form-group");

    const statusGroup =
        document
            .getElementById(
                "edit-status"
            )
            .closest(".form-group");

    const assignedGroup =
        document
            .getElementById(
                "edit-assigned-to"
            )
            .closest(".form-group");

    if (!currentUser) {
        return;
    }

    /*
       USER:
       Can only edit title and description.
    */

    if (
        currentUser.role === "USER"
    ) {

        priorityGroup.style.display =
            "none";

        statusGroup.style.display =
            "none";

        assignedGroup.style.display =
            "none";
    }

    /*
       TECHNICIAN:
       Can edit priority and status.
       Cannot assign.
    */

    else if (
        currentUser.role === "TECHNICIAN"
    ) {

        priorityGroup.style.display =
            "";

        statusGroup.style.display =
            "";

        assignedGroup.style.display =
            "none";
    }

    /*
       ADMIN:
       Can edit everything.
    */

    else if (
        currentUser.role === "ADMIN"
    ) {

        priorityGroup.style.display =
            "";

        statusGroup.style.display =
            "";

        assignedGroup.style.display =
            "";
    }
}


/* =========================
   Edit Submit
========================= */

editForm.addEventListener(
    "submit",
    async event => {

        event.preventDefault();

        editError.textContent = "";

        editError.classList.remove(
            "visible"
        );

        const ticketId =
            editModal.dataset.ticketId;

        const updatedData = {

            title:
                document
                    .getElementById(
                        "edit-title"
                    )
                    .value
                    .trim(),

            description:
                document
                    .getElementById(
                        "edit-description"
                    )
                    .value
                    .trim()
        };

        if (
            currentUser.role ===
                "TECHNICIAN" ||
            currentUser.role ===
                "ADMIN"
        ) {

            updatedData.priority =
                document
                    .getElementById(
                        "edit-priority"
                    )
                    .value;

            updatedData.status =
                document
                    .getElementById(
                        "edit-status"
                    )
                    .value;
        }

        if (
            currentUser.role === "ADMIN"
        ) {

            const assignedValue =
                document
                    .getElementById(
                        "edit-assigned-to"
                    )
                    .value;

            /*
               Empty value means
               unassigned.
            */

            updatedData.assigned_to_id =
                assignedValue
                    ? Number(assignedValue)
                    : null;
        }

        try {

            const response =
                await fetch(
                    `/tickets/${ticketId}`,
                    {
                        method: "PATCH",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body:
                            JSON.stringify(
                                updatedData
                            )
                    }
                );

            const result =
                await response.json();

            if (
                response.status === 401
            ) {
                window.location.href =
                    "/login";

                return;
            }

            if (!response.ok) {

                throw new Error(
                    result.error ||
                    "Failed to update ticket"
                );
            }

            editModal.classList.remove(
                "active"
            );

            await loadTickets();

            await openTicketDetails(
                ticketId
            );

        } catch (error) {

            console.error(
                "Error updating ticket:",
                error
            );

            editError.textContent =
                error.message;

            editError.classList.add(
                "visible"
            );
        }
    }
);


/* =========================
   Close Edit Modal
========================= */

document
    .getElementById(
        "close-edit-modal"
    )
    .addEventListener(
        "click",
        () => {

            editModal.classList.remove(
                "active"
            );
        }
    );


document
    .getElementById(
        "cancel-edit"
    )
    .addEventListener(
        "click",
        () => {

            editModal.classList.remove(
                "active"
            );
        }
    );


editModal.addEventListener(
    "click",
    event => {

        if (
            event.target === editModal
        ) {
            editModal.classList.remove(
                "active"
            );
        }
    }
);


/* =========================================================
   DELETE TICKET
========================================================= */

const deleteTicketBtn =
    document.getElementById(
        "delete-ticket-btn"
    );


deleteTicketBtn.addEventListener(
    "click",
    async () => {

        const detailsModal =
            document.getElementById(
                "details-modal"
            );

        const ticketId =
            detailsModal.dataset.ticketId;

        if (!ticketId) {

            alert(
                "No ticket selected."
            );

            return;
        }

        if (
            !currentUser ||
            currentUser.role !== "ADMIN"
        ) {

            alert(
                "Only administrators can delete tickets."
            );

            return;
        }

        const confirmed =
            confirm(
                `Are you sure you want to delete ticket #${ticketId}?`
            );

        if (!confirmed) {
            return;
        }

        try {

            const response =
                await fetch(
                    `/tickets/${ticketId}`,
                    {
                        method: "DELETE"
                    }
                );

            const result =
                await response.json();

            if (
                response.status === 401
            ) {

                window.location.href =
                    "/login";

                return;
            }

            if (!response.ok) {

                throw new Error(
                    result.error ||
                    "Failed to delete ticket"
                );
            }

            detailsModal.classList.remove(
                "active"
            );

            await loadTickets();

        } catch (error) {

            console.error(
                "Delete error:",
                error
            );

            alert(
                error.message ||
                "Unable to delete ticket."
            );
        }
    }
);


/* =========================================================
   NAVIGATION
========================================================= */

const usersNav =
    document.getElementById(
        "users-nav"
    );

const dashboardNav =
    document.getElementById(
        "dashboard-nav"
    );

const ticketsNav =
    document.getElementById(
        "tickets-nav"
    );

const ticketSection =
    document.getElementById(
        "ticket-management-section"
    );

const userSection =
    document.getElementById(
        "user-management-section"
    );

const pageTitle =
    document.getElementById(
        "page-title"
    );


function showDashboardSection() {

    if (ticketSection) {
        ticketSection.style.display =
            "";
    }

    if (userSection) {
        userSection.style.display =
            currentUser?.role === "ADMIN"
                ? "none"
                : "none";
    }

    if (ticketStats) {
        ticketStats.style.display =
            "";
    }

    if (pageTitle) {
        pageTitle.textContent =
            "Dashboard";
    }

    dashboardNav?.classList.add(
        "active"
    );

    ticketsNav?.classList.remove(
        "active"
    );

    usersNav?.classList.remove(
        "active"
    );
}


function showTicketsSection() {

    if (ticketSection) {
        ticketSection.style.display =
            "";
    }

    if (userSection) {
        userSection.style.display =
            "none";
    }

    if (ticketStats) {
        ticketStats.style.display =
            "";
    }

    if (pageTitle) {
        pageTitle.textContent =
            "Tickets";
    }

    dashboardNav?.classList.remove(
        "active"
    );

    ticketsNav?.classList.add(
        "active"
    );

    usersNav?.classList.remove(
        "active"
    );
}


async function showUsersSection() {

    if (
        !currentUser ||
        currentUser.role !== "ADMIN"
    ) {
        return;
    }

    if (ticketSection) {
        ticketSection.style.display =
            "none";
    }

    if (userSection) {
        userSection.style.display =
            "";
    }

    if (ticketStats) {
        ticketStats.style.display =
            "none";
    }

    if (pageTitle) {
        pageTitle.textContent =
            "User Management";
    }

    dashboardNav?.classList.remove(
        "active"
    );

    ticketsNav?.classList.remove(
        "active"
    );

    usersNav?.classList.add(
        "active"
    );

    await loadUsers();
}


dashboardNav?.addEventListener(
    "click",
    event => {

        event.preventDefault();

        showDashboardSection();
    }
);


ticketsNav?.addEventListener(
    "click",
    event => {

        event.preventDefault();

        showTicketsSection();
    }
);


usersNav?.addEventListener(
    "click",
    async event => {

        event.preventDefault();

        await showUsersSection();
    }
);


/* =========================
   Ticket Statistics Reference
========================= */

const ticketStats =
    document.getElementById(
        "ticket-stats"
    );

document.addEventListener("DOMContentLoaded", async () => {
    const authenticated = await loadCurrentUser();

    if (!authenticated) {
        return;
    }

    activeSettings = getSavedSettings();

    applyDashboardSettings(activeSettings);

    const previousPageButton = document.getElementById(
        "previous-page-button"
    );

    const nextPageButton = document.getElementById(
        "next-page-button"
    );

    if (previousPageButton) {
        previousPageButton.addEventListener("click", () => {
            changeTicketPage(-1);
        });
    }

    if (nextPageButton) {
        nextPageButton.addEventListener("click", () => {
            changeTicketPage(1);
        });
    }

    /*
     * Load tickets for the dashboard.
     */

    await loadTickets();

    /*
     * Start automatic ticket refresh when enabled.
     */

    configureTicketAutoRefresh(activeSettings);

    /*
     * Load users for administrators.
     * This also populates the technician dropdown.
     */

    if (currentUser.role === "ADMIN") {
        await loadUsers();
    }
});
