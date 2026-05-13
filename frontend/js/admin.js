let currentFaqs = [];
let currentUsers = [];
let currentVendors = [];
let currentTickets = [];

document.addEventListener('DOMContentLoaded', () => {
    // Initial load
    switchTab('dashboard');
    
    // Auto-refresh stats every 10 seconds
    setInterval(loadStats, 10000);

    // FAQ Form submission
    document.getElementById('faq-form').addEventListener('submit', handleFAQSubmit);
    
    // User Form submission
    document.getElementById('user-form').addEventListener('submit', handleUserSubmit);
});

async function loadStats() {
    try {
        const res = await fetch('/api/admin/dashboard/stats');
        const data = await res.json();
        
        document.getElementById('stat-active-calls').textContent = data.active_calls;
        document.getElementById('stat-online-agents').textContent = data.online_agents;
        document.getElementById('stat-open-tickets').textContent = data.open_tickets;
        document.getElementById('stat-avg-wait').textContent = data.avg_wait_time;
    } catch (err) {
        console.error('Failed to load stats:', err);
    }
}

function switchTab(tabName) {
    // Hide all sections
    document.querySelectorAll('.section-view').forEach(el => el.classList.remove('active'));
    // Remove active from nav
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    
    // Activate target
    const targetSection = document.getElementById(`${tabName}-section`);
    if (targetSection) targetSection.classList.add('active');
    
    const targetNav = document.querySelector(`[onclick="switchTab('${tabName}')"]`);
    if (targetNav) targetNav.classList.add('active');

    // Data Fetching
    if (tabName === 'dashboard') loadStats();
    if (tabName === 'faqs') loadFAQs();
    if (tabName === 'users') loadUsers();
    if (tabName === 'vendors') loadVendors();
    if (tabName === 'tickets') loadTickets();
}

// --- FAQ Management ---
async function loadFAQs() {
    try {
        const res = await fetch('/api/admin/faqs');
        const data = await res.json();
        currentFaqs = data.faqs || [];
        renderFAQs();
    } catch (err) {
        console.error('Failed to load FAQs:', err);
    }
}

function renderFAQs() {
    const tbody = document.getElementById('faq-table-body');
    tbody.innerHTML = '';
    currentFaqs.forEach((faq, index) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><span class="badge status-pending" style="text-transform:uppercase">${faq.category}</span></td>
            <td>${faq.question_en}</td>
            <td>${faq.question_ne}</td>
            <td class="action-btns">
                <button class="btn-icon" onclick="editFAQ(${index})"><i class="fas fa-edit"></i></button>
                <button class="btn-icon danger" onclick="deleteFAQ(${index})"><i class="fas fa-trash"></i></button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function handleFAQSubmit(e) {
    e.preventDefault();
    const index = document.getElementById('faq-index').value;
    const payload = {
        category: document.getElementById('faq-category').value,
        keywords: document.getElementById('faq-keywords').value.split(',').map(k => k.trim()),
        question_en: document.getElementById('faq-q-en').value,
        question_ne: document.getElementById('faq-q-ne').value,
        answer_en: document.getElementById('faq-a-en').value,
        answer_ne: document.getElementById('faq-a-ne').value,
    };

    const method = index === '-1' ? 'POST' : 'PUT';
    const url = index === '-1' ? '/api/admin/faqs' : `/api/admin/faqs/${index}`;

    const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if (res.ok) { closeModal(); loadFAQs(); }
}

// --- User Management ---
async function loadUsers() {
    try {
        const res = await fetch('/api/admin/users');
        const data = await res.json();
        currentUsers = data.users || [];
        renderUsers();
    } catch (err) { console.error('Failed to load users:', err); }
}

function renderUsers() {
    const tbody = document.getElementById('user-table-body');
    tbody.innerHTML = '';
    currentUsers.forEach(user => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${user.name}</strong></td>
            <td><span class="badge" style="background:rgba(255,255,255,0.05)">${user.role}</span></td>
            <td><span class="badge ${user.status === 'Active' ? 'status-online' : 'status-offline'}">${user.status}</span></td>
            <td class="action-btns">
                <button class="btn-icon" onclick="editUser(${user.id})"><i class="fas fa-edit"></i></button>
                <button class="btn-icon danger" onclick="deleteUser(${user.id})"><i class="fas fa-trash"></i></button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function handleUserSubmit(e) {
    e.preventDefault();
    const id = document.getElementById('user-id').value;
    const payload = {
        name: document.getElementById('user-name').value,
        role: document.getElementById('user-role').value,
        status: document.getElementById('user-status').value
    };

    const method = id === '-1' ? 'POST' : 'PUT';
    const url = id === '-1' ? '/api/admin/users' : `/api/admin/users/${id}`;

    const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if (res.ok) { closeUserModal(); loadUsers(); }
}

// --- Vendors & Tickets (Mock Loaders) ---
async function loadVendors() {
    try {
        const res = await fetch('/api/admin/vendors');
        const data = await res.json();
        const tbody = document.getElementById('vendor-table-body');
        tbody.innerHTML = '';
        data.vendors.forEach(v => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${v.area}</td>
                <td>${v.vendor}</td>
                <td><i class="fas fa-user-circle" style="margin-right:8px"></i>${v.tech}</td>
                <td><span class="badge status-online">${v.status}</span></td>
                <td><button class="btn-icon"><i class="fas fa-cog"></i></button></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) { console.error(err); }
}

async function loadTickets() {
    try {
        const res = await fetch('/api/admin/tickets');
        const data = await res.json();
        const tbody = document.getElementById('tickets-table-body');
        tbody.innerHTML = '';
        data.tickets.forEach(t => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>#${t.id}</td>
                <td>${t.customer}</td>
                <td><span class="badge" style="background:rgba(255,255,255,0.05)">Network</span></td>
                <td><span class="badge" style="background:rgba(255,71,87,0.1); color:#ff4757">High</span></td>
                <td><span class="badge status-pending">${t.status}</span></td>
                <td><button class="btn-icon"><i class="fas fa-arrow-right"></i></button></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) { console.error(err); }
}

// Modal Helpers
function openFAQModal() { document.getElementById('faq-index').value = '-1'; document.getElementById('faq-form').reset(); document.getElementById('faq-modal').classList.add('active'); }
function closeModal() { document.getElementById('faq-modal').classList.remove('active'); }
function openUserModal() { document.getElementById('user-id').value = '-1'; document.getElementById('user-form').reset(); document.getElementById('user-modal').classList.add('active'); }
function closeUserModal() { document.getElementById('user-modal').classList.remove('active'); }

function editFAQ(index) {
    const faq = currentFaqs[index];
    document.getElementById('faq-index').value = index;
    document.getElementById('faq-category').value = faq.category;
    document.getElementById('faq-keywords').value = faq.keywords.join(', ');
    document.getElementById('faq-q-en').value = faq.question_en;
    document.getElementById('faq-q-ne').value = faq.question_ne;
    document.getElementById('faq-a-en').value = faq.answer_en;
    document.getElementById('faq-a-ne').value = faq.answer_ne;
    document.getElementById('faq-modal').classList.add('active');
}

function editUser(id) {
    const user = currentUsers.find(u => u.id === id);
    if (!user) return;
    document.getElementById('user-id').value = user.id;
    document.getElementById('user-name').value = user.name;
    document.getElementById('user-role').value = user.role;
    document.getElementById('user-status').value = user.status;
    document.getElementById('user-modal').classList.add('active');
}
