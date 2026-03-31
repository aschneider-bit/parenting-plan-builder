// ========== State ==========
const STORAGE_KEY = 'ppb_lawyer';
const CLIENTS_KEY = 'ppb_clients';

function getLawyer() {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
}

function saveLawyer(lawyer) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(lawyer));
}

function getClients() {
    const raw = localStorage.getItem(CLIENTS_KEY);
    return raw ? JSON.parse(raw) : [];
}

function saveClients(clients) {
    localStorage.setItem(CLIENTS_KEY, JSON.stringify(clients));
}

function generateToken() {
    return 'xxxx-xxxx-xxxx'.replace(/x/g, () => Math.random().toString(36)[2]);
}

// ========== Screens ==========
function showSetup() {
    document.getElementById('setupScreen').style.display = 'flex';
    document.getElementById('dashboardScreen').style.display = 'none';
    document.getElementById('detailScreen').style.display = 'none';
    document.querySelector('.navbar').style.display = 'none';
}

function showDashboard() {
    const lawyer = getLawyer();
    if (!lawyer) return showSetup();

    document.getElementById('setupScreen').style.display = 'none';
    document.getElementById('dashboardScreen').style.display = 'block';
    document.getElementById('detailScreen').style.display = 'none';
    document.querySelector('.navbar').style.display = 'flex';

    // Set avatar
    const parts = lawyer.lawyer_name.split(' ');
    const initials = parts.length >= 2
        ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
        : lawyer.lawyer_name.substring(0, 2).toUpperCase();
    document.getElementById('avatarInitials').textContent = initials;
    document.getElementById('previewFirmName').textContent = lawyer.firm_name;

    renderClients();
}

function showDetail(clientId) {
    const lawyer = getLawyer();
    const clients = getClients();
    const client = clients.find(c => c.id === clientId);
    if (!client || !client.intake) return;

    document.getElementById('setupScreen').style.display = 'none';
    document.getElementById('dashboardScreen').style.display = 'none';
    document.getElementById('detailScreen').style.display = 'block';
    document.querySelector('.navbar').style.display = 'flex';

    const intake = client.intake;
    document.getElementById('detailName').textContent = intake.full_name || 'Client Details';

    const sections = [
        {
            title: 'Personal Information',
            badge: `Submitted ${new Date(intake.submitted_at).toLocaleDateString()}`,
            fields: [
                ['Full Name', intake.full_name], ['Maiden Name', intake.maiden_name],
                ['Date of Birth', intake.birth_date], ['City/State Where Born', intake.city_state_born],
                ["Driver's License (Last 3)", intake.drivers_license_last3], ['SSN (Last 3)', intake.ssn_last3],
            ]
        },
        {
            title: 'Contact Information',
            fields: [
                ['Address', intake.address], ['City', intake.city],
                ['County', intake.county], ['State', intake.state],
                ['Zip', intake.zip], ['Phone', intake.phone], ['Email', intake.email],
            ]
        },
        {
            title: 'Employment Information',
            fields: [
                ['Employer', intake.employer], ['Job Title', intake.job_title],
                ['Employer Address', intake.employer_address],
                ['Employer City/State/Zip', intake.employer_city_state_zip],
                ['Gross Salary', intake.gross_salary],
                ['Length of Employment', intake.length_of_employment],
                ['Education', intake.education],
            ]
        }
    ];

    let html = '';
    for (const sec of sections) {
        html += `<div class="card"><div class="card-header"><h2>${sec.title}</h2>`;
        if (sec.badge) html += `<span class="badge badge-completed">${sec.badge}</span>`;
        html += `</div><div class="form-row" style="flex-wrap:wrap;">`;
        for (const [label, value] of sec.fields) {
            html += `<div class="form-group" style="flex:1;min-width:200px;">
                <label>${label}</label>
                <input type="text" value="${value || ''}" readonly style="background:var(--ofw-gray-100);">
            </div>`;
        }
        html += `</div></div>`;
    }

    document.getElementById('detailContent').innerHTML = html;

    // Store current client for PDF
    window._currentClient = client;
}

// ========== Render Clients ==========
function renderClients() {
    const clients = getClients();
    const total = clients.length;
    const pending = clients.filter(c => c.status === 'pending').length;
    const completed = clients.filter(c => c.status === 'completed').length;

    document.getElementById('statTotal').textContent = total;
    document.getElementById('statPending').textContent = pending;
    document.getElementById('statCompleted').textContent = completed;

    const el = document.getElementById('clientList');

    if (total === 0) {
        el.innerHTML = `<div class="empty-state">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.4">
                <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/>
                <line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/>
            </svg>
            <h3>No clients yet</h3>
            <p>Click "New Client" to create an intake link and send it to your client.</p>
        </div>`;
        return;
    }

    let html = `<div class="table-wrapper"><table><thead><tr>
        <th>Client</th><th>Status</th><th>Created</th><th>Completed</th><th>Actions</th>
    </tr></thead><tbody>`;

    for (const c of clients) {
        const name = c.intake ? c.intake.full_name : 'Pending intake';
        const email = c.intake ? c.intake.email : '';
        const statusBadge = c.status === 'completed'
            ? '<span class="badge badge-completed">Completed</span>'
            : '<span class="badge badge-pending">Pending</span>';
        const created = new Date(c.created_at).toLocaleDateString();
        const completedDate = c.completed_at ? new Date(c.completed_at).toLocaleDateString() : '—';

        let actions = '';
        if (c.status === 'pending') {
            actions = `<button class="btn btn-outline btn-sm" onclick="showShareLink('${c.token}')">Share Link</button>`;
        } else {
            actions = `<button class="btn btn-outline btn-sm" onclick="showDetail('${c.id}')">View</button>
                       <button class="btn btn-primary btn-sm" onclick="showDetail('${c.id}');setTimeout(downloadPdf,100);">PDF</button>`;
        }

        html += `<tr>
            <td><strong>${name}</strong>${email ? `<br><span style="font-size:12px;color:var(--ofw-gray-500);">${email}</span>` : ''}</td>
            <td>${statusBadge}</td>
            <td>${created}</td>
            <td>${completedDate}</td>
            <td><div class="actions-cell">${actions}</div></td>
        </tr>`;
    }

    html += `</tbody></table></div>`;
    el.innerHTML = html;

    // Check for any completed intake data from the intake page (same browser)
    checkForCompletedIntakes();
}

function checkForCompletedIntakes() {
    const clients = getClients();
    let updated = false;

    for (const c of clients) {
        if (c.status === 'pending') {
            const intakeData = localStorage.getItem(`intake_data_${c.token}`);
            if (intakeData) {
                c.status = 'completed';
                c.completed_at = new Date().toISOString();
                c.intake = JSON.parse(intakeData);
                updated = true;
            }
        }
    }

    if (updated) {
        saveClients(clients);
        renderClients();
    }
}

// ========== Actions ==========
function createClient() {
    const lawyer = getLawyer();
    const token = generateToken();
    const clients = getClients();

    clients.unshift({
        id: 'client_' + Date.now(),
        token: token,
        status: 'pending',
        created_at: new Date().toISOString(),
        completed_at: null,
        intake: null,
    });

    saveClients(clients);

    // Show share link immediately
    showShareLink(token);
    renderClients();
}

function showShareLink(token) {
    const lawyer = getLawyer();
    const baseUrl = window.location.href.replace(/index\.html.*$/, '').replace(/\/$/, '');
    const params = new URLSearchParams({
        firm: lawyer.firm_name,
        lawyer: lawyer.lawyer_name,
        token: token,
    });
    const link = `${baseUrl}/intake.html?${params.toString()}`;
    document.getElementById('shareLinkInput').value = link;
    openModal('shareLinkModal');
}

function copyLink() {
    const input = document.getElementById('shareLinkInput');
    input.select();
    navigator.clipboard.writeText(input.value).then(() => showToast('Link copied to clipboard!'));
}

function downloadPdf() {
    const lawyer = getLawyer();
    const client = window._currentClient;
    if (!client || !client.intake) return;

    const data = client.intake;
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    let y = 20;

    doc.setFontSize(16);
    doc.setFont('helvetica', 'bold');
    doc.text(lawyer.firm_name, 105, y, { align: 'center' }); y += 7;
    doc.setFontSize(11);
    doc.setFont('helvetica', 'normal');
    doc.text(`Attorney: ${lawyer.lawyer_name}`, 105, y, { align: 'center' }); y += 5;
    if (lawyer.email) { doc.text(lawyer.email, 105, y, { align: 'center' }); y += 5; }
    if (lawyer.phone) { doc.text(lawyer.phone, 105, y, { align: 'center' }); y += 5; }
    y += 3;

    doc.setDrawColor(0, 82, 136);
    doc.setLineWidth(0.5);
    doc.line(10, y, 200, y); y += 8;

    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.text('Client Intake Form - Completed', 105, y, { align: 'center' }); y += 6;
    if (data.submitted_at) {
        doc.setFontSize(9);
        doc.setFont('helvetica', 'italic');
        doc.text(`Submitted: ${new Date(data.submitted_at).toLocaleDateString()}`, 105, y, { align: 'center' }); y += 10;
    }

    function section(title) {
        if (y > 260) { doc.addPage(); y = 20; }
        doc.setFillColor(0, 82, 136);
        doc.rect(10, y, 190, 8, 'F');
        doc.setTextColor(255, 255, 255);
        doc.setFontSize(11);
        doc.setFont('helvetica', 'bold');
        doc.text(`  ${title}`, 12, y + 5.5);
        doc.setTextColor(0, 0, 0);
        y += 12;
    }

    function field(label, value) {
        if (y > 275) { doc.addPage(); y = 20; }
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(10);
        doc.text(`${label}:`, 14, y);
        doc.setFont('helvetica', 'normal');
        doc.text(value || 'N/A', 70, y);
        y += 7;
    }

    section('Personal Information');
    field('Full Name', data.full_name);
    field('Maiden Name', data.maiden_name);
    field('Date of Birth', data.birth_date);
    field('City/State Born', data.city_state_born);
    field("Driver's License (Last 3)", data.drivers_license_last3);
    field('SSN (Last 3)', data.ssn_last3);
    y += 4;

    section('Contact Information');
    field('Address', data.address);
    field('City', data.city);
    field('County', data.county);
    field('State', data.state);
    field('Zip', data.zip);
    field('Phone', data.phone);
    field('Email', data.email);
    y += 4;

    section('Employment Information');
    field('Employer', data.employer);
    field('Job Title', data.job_title);
    field('Employer Address', data.employer_address);
    field('Employer City/State/Zip', data.employer_city_state_zip);
    field('Gross Salary', data.gross_salary);
    field('Length of Employment', data.length_of_employment);
    field('Education', data.education);

    y += 10;
    doc.setDrawColor(0, 82, 136);
    doc.line(10, y, 200, y); y += 5;
    doc.setFontSize(8);
    doc.setFont('helvetica', 'italic');
    doc.text('Generated by OurFamilyWizard Pro - Parenting Plan Builder', 105, y, { align: 'center' });

    doc.save(`intake_${(data.full_name || 'client').replace(/\s+/g, '_')}.pdf`);
}

// ========== UI Helpers ==========
function openModal(id) { document.getElementById(id).classList.add('active'); }
function closeModal(id) { document.getElementById(id).classList.remove('active'); }

function showToast(msg) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 3000);
}

// ========== Setup Form ==========
document.getElementById('setupForm').addEventListener('submit', function(e) {
    e.preventDefault();
    const lawyer = {
        firm_name: document.getElementById('setupFirmName').value,
        lawyer_name: document.getElementById('setupLawyerName').value,
        email: document.getElementById('setupEmail').value,
        phone: document.getElementById('setupPhone').value,
    };
    saveLawyer(lawyer);
    showDashboard();
});

// ========== Init ==========
(function init() {
    const lawyer = getLawyer();
    if (lawyer) {
        showDashboard();
    } else {
        showSetup();
    }
})();
