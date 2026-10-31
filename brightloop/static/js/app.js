/**
 * Brightloop Software - Ultra-Modern Subscription Management Client Application
 * Precision UI, Ambient Dynamics & Instant Interactivity
 */

const STATE = {
  currentPersona: 'admin', // 'admin', 'staff', 'customer'
  activeView: 'dashboard',
  subscriptions: [],
  invoices: [],
  payments: [],
  products: [],
  plans: [],
  templates: [],
  discounts: [],
  taxes: [],
  customers: [],
  activeSubFilter: 'all',
  activeInvFilter: 'all',
  theme: localStorage.getItem('brightloop_theme') || 'light'
};

// ======================== THEME MANAGER ========================

function initTheme() {
  const saved = localStorage.getItem('brightloop_theme') || 'light';
  applyTheme(saved);
}

function toggleTheme() {
  const newTheme = STATE.theme === 'dark' ? 'light' : 'dark';
  applyTheme(newTheme);
  showToast(`Switched to ${newTheme === 'dark' ? 'Dark' : 'Light'} theme`, 'info');
}

function applyTheme(theme) {
  STATE.theme = theme;
  localStorage.setItem('brightloop_theme', theme);
  const icon = document.getElementById('theme-icon');
  if (theme === 'dark') {
    document.documentElement.setAttribute('data-theme', 'dark');
    if (icon) icon.innerText = '☀️';
  } else {
    document.documentElement.removeAttribute('data-theme');
    if (icon) icon.innerText = '🌙';
  }
}

// ======================== API CLIENT ========================

async function api(path, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    'X-Demo-Role': STATE.currentPersona,
    ...(options.headers || {})
  };

  try {
    const res = await fetch(path, { ...options, headers });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || 'Server error occurred');
    }
    return data;
  } catch (err) {
    showToast(err.message, 'error');
    throw err;
  }
}

// ======================== NOTIFICATIONS ========================

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  
  const icon = type === 'success' ? '✅' : type === 'error' ? '⚠️' : 'ℹ️';
  toast.innerHTML = `<span style="font-size:16px;">${icon}</span><div>${message}</div>`;
  container.appendChild(toast);
  
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(20px)';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// ======================== LIVE TABLE SEARCH ========================

function filterTable(inputEl, tableBodyId) {
  const term = (inputEl.value || '').toLowerCase().trim();
  const tbody = document.getElementById(tableBodyId);
  if (!tbody) return;

  const rows = tbody.querySelectorAll('tr');
  let matchCount = 0;

  rows.forEach(row => {
    if (row.classList.contains('no-results-row')) return;
    const text = row.innerText.toLowerCase();
    if (!term || text.includes(term)) {
      row.style.display = '';
      matchCount++;
    } else {
      row.style.display = 'none';
    }
  });

  // Handle empty search feedback
  const existingNoRes = tbody.querySelector('.no-results-row');
  if (existingNoRes) existingNoRes.remove();

  if (matchCount === 0 && term) {
    const colCount = rows[0] ? rows[0].cells.length : 6;
    const noRow = document.createElement('tr');
    noRow.className = 'no-results-row';
    noRow.innerHTML = `<td colspan="${colCount}" style="text-align:center; padding:24px; color:var(--text-muted);">
      🔍 No matching records found for "<strong>${term}</strong>".
    </td>`;
    tbody.appendChild(noRow);
  }
}

// ======================== PERSONA SWITCHER ========================

function switchPersona(persona) {
  STATE.currentPersona = persona;

  document.querySelectorAll('.persona-btn').forEach(btn => btn.classList.remove('active'));
  const targetBtn = document.getElementById(`btn-persona-${persona}`);
  if (targetBtn) targetBtn.classList.add('active');

  const roleTag = document.getElementById('active-user-role');
  const nameTag = document.getElementById('active-user-name');
  const avatarTag = document.getElementById('active-user-avatar');
  const quickBillingBtn = document.getElementById('btn-quick-billing');
  const adminCatalog = document.getElementById('admin-nav-group-catalog');
  const adminSystem = document.getElementById('admin-nav-group-system');
  const navDiscounts = document.getElementById('nav-discounts');
  const navTaxes = document.getElementById('nav-taxes');
  const navStaff = document.getElementById('nav-staff');
  const customerNavGroup = document.getElementById('customer-nav-group');
  const navPortal = document.getElementById('nav-portal');
  const btnAddProduct = document.getElementById('btn-add-product');
  const btnAddPlan = document.getElementById('btn-add-plan');

  if (persona === 'admin') {
    if (nameTag) nameTag.innerText = 'Arthur Dent';
    if (roleTag) {
      roleTag.innerText = 'Admin';
      roleTag.style.background = 'var(--primary-light)';
      roleTag.style.color = 'var(--primary)';
    }
    if (avatarTag) avatarTag.innerText = 'AD';
    if (quickBillingBtn) quickBillingBtn.style.display = 'flex';
    if (adminCatalog) adminCatalog.style.display = 'block';
    if (adminSystem) adminSystem.style.display = 'block';
    if (navDiscounts) navDiscounts.style.display = 'flex';
    if (navTaxes) navTaxes.style.display = 'flex';
    if (navStaff) navStaff.style.display = 'flex';
    if (customerNavGroup) customerNavGroup.style.display = 'none';
    if (navPortal) navPortal.style.display = 'none';
    if (btnAddProduct) btnAddProduct.style.display = 'inline-flex';
    if (btnAddPlan) btnAddPlan.style.display = 'inline-flex';
    navigateTo('dashboard');
  } else if (persona === 'staff') {
    if (nameTag) nameTag.innerText = 'Sarah Connor';
    if (roleTag) {
      roleTag.innerText = 'Staff';
      roleTag.style.background = 'var(--secondary-light)';
      roleTag.style.color = 'var(--secondary)';
    }
    if (avatarTag) avatarTag.innerText = 'SC';
    if (quickBillingBtn) quickBillingBtn.style.display = 'flex';
    if (adminCatalog) adminCatalog.style.display = 'block';
    if (adminSystem) adminSystem.style.display = 'none';
    if (navDiscounts) navDiscounts.style.display = 'none';
    if (navTaxes) navTaxes.style.display = 'none';
    if (navStaff) navStaff.style.display = 'none';
    if (customerNavGroup) customerNavGroup.style.display = 'none';
    if (navPortal) navPortal.style.display = 'none';
    if (btnAddProduct) btnAddProduct.style.display = 'none';
    if (btnAddPlan) btnAddPlan.style.display = 'none';
    navigateTo('dashboard');
  } else if (persona === 'customer') {
    if (nameTag) nameTag.innerText = 'Alex Mercer';
    if (roleTag) {
      roleTag.innerText = 'Customer';
      roleTag.style.background = 'var(--success-light)';
      roleTag.style.color = 'var(--success)';
    }
    if (avatarTag) avatarTag.innerText = 'AM';
    if (quickBillingBtn) quickBillingBtn.style.display = 'none';
    if (adminCatalog) adminCatalog.style.display = 'none';
    if (adminSystem) adminSystem.style.display = 'none';
    if (navDiscounts) navDiscounts.style.display = 'none';
    if (navTaxes) navTaxes.style.display = 'none';
    if (navStaff) navStaff.style.display = 'none';
    if (customerNavGroup) customerNavGroup.style.display = 'block';
    if (navPortal) navPortal.style.display = 'flex';
    navigateTo('portal');
  }

  showToast(`Switched persona to ${roleTag.innerText}: ${nameTag.innerText}`, 'success');
}

// ======================== NAVIGATION ========================

function navigateTo(viewId, subFilter = null) {
  STATE.activeView = viewId;

  // Update sidebar active link
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
  const activeNav = document.getElementById(`nav-${viewId}`);
  if (activeNav) activeNav.classList.add('active');

  // Update view panel
  document.querySelectorAll('.view-panel').forEach(panel => panel.classList.remove('active'));
  const targetPanel = document.getElementById(`view-${viewId}`);
  if (targetPanel) targetPanel.classList.add('active');

  // Load relevant data
  if (viewId === 'dashboard') loadDashboard();
  else if (viewId === 'subscriptions') loadSubscriptions();
  else if (viewId === 'templates') loadTemplates();
  else if (viewId === 'invoices') {
    if (subFilter === 'overdue') {
      const tab = document.querySelector('.filter-tab[onclick*="overdue"]');
      filterInvoices('overdue', tab);
    } else {
      loadInvoices();
    }
  }
  else if (viewId === 'payments') loadPayments();
  else if (viewId === 'products') loadProducts();
  else if (viewId === 'plans') loadPlans();
  else if (viewId === 'discounts') loadDiscounts();
  else if (viewId === 'taxes') loadTaxes();
  else if (viewId === 'staff') loadStaff();
  else if (viewId === 'portal') loadPortal();
}

// ======================== DASHBOARD LOADER ========================

async function loadDashboard() {
  try {
    const data = await api('/api/reports/dashboard');

    document.getElementById('kpi-active-subs').innerText = data.active_subscriptions;
    document.getElementById('kpi-mrr').innerText = `$${data.mrr.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    document.getElementById('kpi-arr').innerText = `ARR: $${data.arr.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    document.getElementById('kpi-total-revenue').innerText = `$${data.total_revenue.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    document.getElementById('kpi-overdue-amt').innerText = `$${data.overdue_amount.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    document.getElementById('kpi-overdue-cnt').innerText = `${data.overdue_count} overdue invoice(s)`;

    // Update Overdue Bar Fill
    const overdueBar = document.getElementById('overdue-bar');
    if (overdueBar) {
      const pct = data.overdue_count > 0 ? Math.min(100, data.overdue_count * 20) : 0;
      overdueBar.style.width = `${pct}%`;
    }

    // Render Overdue Invoices Chasing Table
    const odBody = document.getElementById('table-overdue-body');
    if (!data.overdue_invoices || data.overdue_invoices.length === 0) {
      odBody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--success); font-weight:700; padding:28px;">
        <span style="font-size:20px; display:block; margin-bottom:6px;">🎉</span>
        All clean! No overdue receivables requiring chasing at this time.
      </td></tr>`;
    } else {
      odBody.innerHTML = data.overdue_invoices.map(inv => `
        <tr>
          <td><strong style="font-family:var(--font-mono); color:var(--primary);">${inv.invoice_number}</strong></td>
          <td><strong>${inv.customer_name}</strong></td>
          <td style="color:var(--text-secondary);">${inv.customer_email}</td>
          <td><span class="badge badge-overdue"><span class="status-dot" style="background:var(--danger);"></span>${inv.due_date} (Overdue)</span></td>
          <td class="tabular-nums" style="font-weight:600;">$${inv.total_amount.toFixed(2)}</td>
          <td class="tabular-nums" style="color:var(--danger); font-weight:800; font-family:var(--font-mono);">$${inv.balance_due.toFixed(2)}</td>
          <td>
            <div style="display:flex; gap:6px;">
              <button class="btn btn-primary btn-sm" onclick="sendInvoiceReminder(${inv.id})">✉️ Remind</button>
              <button class="btn btn-secondary btn-sm" onclick="openPaymentForInvoice(${inv.id}, '${inv.invoice_number}', ${inv.balance_due}, '${inv.customer_name}')">💳 Pay</button>
              <button class="btn btn-outline btn-sm" onclick="viewPrintInvoice(${inv.id})">View</button>
            </div>
          </td>
        </tr>
      `).join('');
    }

    // Render Recent Payments
    const payBody = document.getElementById('table-recent-payments-body');
    if (!data.recent_payments || data.recent_payments.length === 0) {
      payBody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:24px; color:var(--text-muted);">No payment transactions recorded yet.</td></tr>`;
    } else {
      payBody.innerHTML = data.recent_payments.map(p => `
        <tr>
          <td><strong style="font-family:var(--font-mono);">${p.payment_number}</strong></td>
          <td><code style="font-size:12px;">${p.invoice_number}</code></td>
          <td><strong>${p.customer_name}</strong></td>
          <td><span class="badge" style="background:var(--secondary-light); color:var(--secondary); border:1px solid rgba(14,165,233,0.2);">${p.payment_method}</span></td>
          <td class="tabular-nums" style="font-weight:800; color:var(--success); font-family:var(--font-mono);">$${p.amount.toFixed(2)}</td>
          <td style="color:var(--text-secondary);">${p.payment_date}</td>
          <td style="color:var(--text-muted);">${p.note || '-'}</td>
        </tr>
      `).join('');
    }

  } catch (err) {
    console.error('Failed to load dashboard:', err);
  }
}

// ======================== SUBSCRIPTIONS LOADER ========================

async function loadSubscriptions() {
  try {
    const subs = await api('/api/subscriptions');
    STATE.subscriptions = subs;
    document.getElementById('count-subs').innerText = subs.length;
    renderSubscriptionsTable();
  } catch (err) {
    console.error(err);
  }
}

function filterSubs(status, element) {
  STATE.activeSubFilter = status;
  if (element) {
    document.querySelectorAll('#view-subscriptions .filter-tab').forEach(t => t.classList.remove('active'));
    element.classList.add('active');
  }
  renderSubscriptionsTable();
}

function renderSubscriptionsTable() {
  const filtered = STATE.subscriptions.filter(s => {
    if (STATE.activeSubFilter === 'all') return true;
    return s.status === STATE.activeSubFilter;
  });

  const tbody = document.getElementById('table-subs-body');
  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:32px; color:var(--text-muted);">
      <div style="font-size:24px; margin-bottom:6px;">🔄</div>
      No subscriptions found in "<strong>${STATE.activeSubFilter}</strong>" stage.
    </td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(s => {
    let actionsHtml = '';

    if (s.status === 'draft') {
      actionsHtml = `
        <button class="btn btn-sm btn-outline" onclick="advanceSubStatus(${s.id}, 'quotation')">Make Quote &rarr;</button>
      `;
    } else if (s.status === 'quotation') {
      actionsHtml = `
        <button class="btn btn-sm btn-outline" onclick="advanceSubStatus(${s.id}, 'confirmed')">Confirm Offer &rarr;</button>
      `;
    } else if (s.status === 'confirmed') {
      actionsHtml = `
        <button class="btn btn-sm btn-primary" onclick="advanceSubStatus(${s.id}, 'active')">Activate ⚡</button>
      `;
    } else if (s.status === 'active') {
      let pauseBtn = s.allow_pause ? `<button class="btn btn-sm btn-outline" onclick="advanceSubStatus(${s.id}, 'paused')">Pause</button>` : '';
      let closeBtn = s.allow_close_early ? `<button class="btn btn-sm btn-outline" style="color:var(--danger); border-color:var(--danger-border);" onclick="advanceSubStatus(${s.id}, 'closed')">Close Early</button>` : '';
      actionsHtml = `${pauseBtn} ${closeBtn}`;
    } else if (s.status === 'paused') {
      actionsHtml = `
        <button class="btn btn-sm btn-secondary" onclick="advanceSubStatus(${s.id}, 'active')">Resume</button>
      `;
    } else if (s.status === 'closed') {
      actionsHtml = s.allow_renewal ? `<button class="btn btn-sm btn-outline" onclick="advanceSubStatus(${s.id}, 'active')">Renew</button>` : '<span style="color:var(--text-muted); font-size:12px;">Closed</span>';
    }

    return `
      <tr>
        <td><strong style="font-family:var(--font-mono); color:var(--primary);">${s.subscription_number}</strong></td>
        <td>
          <div style="font-weight:700;">${s.customer_name}</div>
          <div style="font-size:11px; color:var(--text-muted);">${s.company_name || ''}</div>
        </td>
        <td>
          <strong>${s.plan_name}</strong>
          <div style="font-size:11px; text-transform:capitalize; color:var(--secondary); font-weight:600;">
            ${s.billing_frequency} ($${s.base_price}/cycle)
          </div>
        </td>
        <td>
          <span class="badge badge-${s.status}">
            <span class="status-dot"></span>
            ${s.status}
          </span>
        </td>
        <td style="color:var(--text-secondary);">${s.start_date}</td>
        <td style="color:var(--text-secondary);">${s.expiry_date || '<span style="color:var(--text-muted);">Ongoing</span>'}</td>
        <td>${s.next_billing_date ? `<strong style="color:var(--primary); font-family:var(--font-mono);">${s.next_billing_date}</strong>` : '<span style="color:var(--text-muted);">-</span>'}</td>
        <td>
          <div style="display:flex; gap:6px;">
            ${actionsHtml}
            <button class="btn btn-sm btn-outline" onclick="openSubscriptionDetails(${s.id})">Details</button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

async function advanceSubStatus(subId, newStatus) {
  try {
    const res = await api(`/api/subscriptions/${subId}/status`, {
      method: 'POST',
      body: JSON.stringify({ status: newStatus })
    });
    showToast(res.message, 'success');
    loadSubscriptions();
    loadDashboard();
  } catch (err) {
    // Error handled in api()
  }
}

// ======================== QUOTATION TEMPLATES ========================

async function loadTemplates() {
  try {
    const tmpls = await api('/api/templates');
    STATE.templates = tmpls;
    const tbody = document.getElementById('table-templates-body');

    if (tmpls.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:24px; color:var(--text-muted);">No quotation templates configured.</td></tr>`;
      return;
    }

    tbody.innerHTML = tmpls.map(t => `
      <tr>
        <td><strong>${t.name}</strong></td>
        <td><span class="badge badge-confirmed">${t.plan_name} (${t.billing_frequency})</span></td>
        <td>${t.validity_days} Days</td>
        <td>
          <div style="display:flex; flex-direction:column; gap:2px; font-size:12px;">
            ${t.lines.map(l => `<div>• <strong>${l.quantity}x</strong> ${l.product_name} ${l.attribute_value ? `<span style="color:var(--secondary); font-weight:600;">(${l.attribute_value})</span>` : ''}</div>`).join('')}
          </div>
        </td>
        <td>
          <button class="btn btn-primary btn-sm" onclick="createQuoteFromTemplatePrompt(${t.id}, '${t.name}')">
            Create Quote for Client &rarr;
          </button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    console.error(err);
  }
}

async function createQuoteFromTemplatePrompt(tmplId, tmplName) {
  await ensureCustomersLoaded();
  const options = STATE.customers.map(c => `${c.id}: ${c.full_name} (${c.company_name || c.email})`).join('\n');
  const custId = prompt(`Create Quotation from template "${tmplName}"\nEnter Customer ID:\n${options}`, STATE.customers[0] ? STATE.customers[0].id : '3');
  
  if (!custId) return;

  try {
    const res = await api(`/api/templates/${tmplId}/create-quote`, {
      method: 'POST',
      body: JSON.stringify({ customer_id: parseInt(custId) })
    });
    showToast(`Quotation ${res.subscription_number} created successfully!`, 'success');
    navigateTo('subscriptions');
  } catch (err) {
    // handled
  }
}

// ======================== INVOICES LOADER ========================

async function loadInvoices() {
  try {
    let url = '/api/invoices';
    if (STATE.activeInvFilter === 'overdue') url += '?overdue_only=1';
    else if (STATE.activeInvFilter !== 'all') url += `?status=${STATE.activeInvFilter}`;

    const invs = await api(url);
    STATE.invoices = invs;
    document.getElementById('count-invoices').innerText = invs.length;

    const tbody = document.getElementById('table-invoices-body');
    if (invs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding:32px; color:var(--text-muted);">No invoices found for this filter.</td></tr>`;
      return;
    }

    const todayStr = new Date().toISOString().split('T')[0];

    tbody.innerHTML = invs.map(inv => {
      const isOverdue = inv.status === 'confirmed' && inv.due_date < todayStr && inv.balance_due > 0;
      const statusBadge = isOverdue 
        ? '<span class="badge badge-overdue"><span class="status-dot" style="background:var(--danger);"></span>OVERDUE</span>' 
        : `<span class="badge badge-${inv.status}"><span class="status-dot"></span>${inv.status}</span>`;

      return `
        <tr>
          <td><strong style="font-family:var(--font-mono); color:var(--primary);">${inv.invoice_number}</strong></td>
          <td><code style="font-size:12px;">${inv.subscription_number || '-'}</code></td>
          <td><strong>${inv.customer_name}</strong></td>
          <td style="color:var(--text-secondary);">${inv.issue_date}</td>
          <td style="${isOverdue ? 'color:var(--danger); font-weight:800;' : 'color:var(--text-secondary);'}">${inv.due_date}</td>
          <td class="tabular-nums" style="font-weight:700; font-family:var(--font-mono);">$${inv.total_amount.toFixed(2)}</td>
          <td class="tabular-nums" style="${inv.balance_due > 0 ? 'color:var(--danger); font-weight:800; font-family:var(--font-mono);' : 'color:var(--success); font-weight:700;'}">$${inv.balance_due.toFixed(2)}</td>
          <td>${statusBadge}</td>
          <td>
            <div style="display:flex; gap:6px;">
              <button class="btn btn-outline btn-sm" onclick="viewPrintInvoice(${inv.id})">🖨️ View/Print</button>
              ${inv.status === 'draft' ? `<button class="btn btn-outline btn-sm" onclick="updateInvoiceStatus(${inv.id}, 'confirmed')">Confirm</button>` : ''}
              ${inv.status === 'confirmed' && inv.balance_due > 0 ? `
                <button class="btn btn-primary btn-sm" onclick="openPaymentForInvoice(${inv.id}, '${inv.invoice_number}', ${inv.balance_due}, '${inv.customer_name}')">💳 Pay</button>
              ` : ''}
              <button class="btn btn-outline btn-sm" onclick="sendInvoiceReminder(${inv.id})">✉️ Send</button>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error(err);
  }
}

function filterInvoices(filter, element) {
  STATE.activeInvFilter = filter;
  if (element) {
    document.querySelectorAll('#view-invoices .filter-tab').forEach(t => t.classList.remove('active'));
    element.classList.add('active');
  }
  loadInvoices();
}

async function updateInvoiceStatus(invId, status) {
  try {
    const res = await api(`/api/invoices/${invId}/status`, {
      method: 'POST',
      body: JSON.stringify({ status })
    });
    showToast(res.message, 'success');
    loadInvoices();
    loadDashboard();
  } catch (err) {}
}

async function sendInvoiceReminder(invId) {
  try {
    const res = await api(`/api/invoices/${invId}/send`, { method: 'POST' });
    showToast(res.message, 'success');
  } catch (err) {}
}

// ======================== PAYMENTS LOADER ========================

async function loadPayments() {
  try {
    const pays = await api('/api/payments');
    STATE.payments = pays;
    const tbody = document.getElementById('table-all-payments-body');
    if (pays.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:32px; color:var(--text-muted);">No payment transactions recorded yet.</td></tr>`;
      return;
    }
    tbody.innerHTML = pays.map(p => `
      <tr>
        <td><strong style="font-family:var(--font-mono);">${p.payment_number}</strong></td>
        <td><code style="font-size:12px;">${p.invoice_number}</code></td>
        <td><strong>${p.customer_name}</strong></td>
        <td><span class="badge" style="background:var(--secondary-light); color:var(--secondary); border:1px solid rgba(14,165,233,0.2);">${p.payment_method}</span></td>
        <td class="tabular-nums" style="font-weight:800; color:var(--success); font-family:var(--font-mono);">$${p.amount.toFixed(2)}</td>
        <td style="color:var(--text-secondary);">${p.payment_date}</td>
        <td style="color:var(--text-muted);">${p.note || '-'}</td>
      </tr>
    `).join('');
  } catch (err) {
    console.error(err);
  }
}

// ======================== PRODUCTS & VARIANTS ========================

async function loadProducts() {
  try {
    const prods = await api('/api/products');
    STATE.products = prods;
    const tbody = document.getElementById('table-products-body');
    tbody.innerHTML = prods.map(p => `
      <tr>
        <td>
          <strong>${p.name}</strong>
          <div style="font-size:11.5px; color:var(--text-muted);">${p.notes || ''}</div>
        </td>
        <td><span class="badge badge-draft">${p.type}</span></td>
        <td class="tabular-nums" style="font-weight:700; font-family:var(--font-mono);">$${p.sales_price.toFixed(2)}</td>
        <td class="tabular-nums" style="color:var(--text-secondary); font-family:var(--font-mono);">$${p.cost_price.toFixed(2)}</td>
        <td>
          ${p.variants && p.variants.length > 0 ? p.variants.map(v => `
            <div style="margin-bottom:3px; display:inline-block; margin-right:8px;">
              • <strong>${v.attribute_value}</strong> 
              ${v.price_surcharge > 0 ? `<span style="color:var(--primary); font-weight:700; font-family:var(--font-mono);">(+$${v.price_surcharge.toFixed(2)})</span>` : '<span style="color:var(--text-muted);">(Base)</span>'}
            </div>
          `).join('') : '<span style="color:var(--text-muted);">Standard base variant only</span>'}
        </td>
      </tr>
    `).join('');
  } catch (err) {
    console.error(err);
  }
}

// ======================== PLANS & POLICIES ========================

async function loadPlans() {
  try {
    const plans = await api('/api/plans');
    STATE.plans = plans;
    const tbody = document.getElementById('table-plans-body');
    tbody.innerHTML = plans.map(p => `
      <tr>
        <td><strong>${p.name}</strong></td>
        <td><code>${p.code}</code></td>
        <td><span class="badge badge-confirmed" style="text-transform:capitalize;">${p.billing_frequency}</span></td>
        <td class="tabular-nums" style="font-weight:800; font-family:var(--font-mono);">$${p.base_price.toFixed(2)}</td>
        <td>${p.min_quantity} seat(s)</td>
        <td>${p.auto_close ? '<span class="badge badge-paused">Auto-Closes</span>' : '<span style="color:var(--text-muted); font-size:12px;">Manual / Ongoing</span>'}</td>
        <td>
          <div style="font-size:11px; display:flex; flex-wrap:wrap; gap:4px;">
            ${p.allow_pause ? '<span class="badge badge-active">Can Pause</span>' : '<span class="badge badge-closed">No Pause</span>'}
            ${p.allow_close_early ? '<span class="badge badge-active">Early Close</span>' : '<span class="badge badge-closed">Locked</span>'}
            ${p.allow_renewal ? '<span class="badge badge-active">Renewable</span>' : '<span class="badge badge-closed">No Renew</span>'}
          </div>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    console.error(err);
  }
}

// ======================== DISCOUNTS ========================

async function loadDiscounts() {
  try {
    const discs = await api('/api/discounts');
    STATE.discounts = discs;
    const tbody = document.getElementById('table-discounts-body');
    tbody.innerHTML = discs.map(d => `
      <tr>
        <td><code style="font-weight:700; font-size:12px;">${d.code}</code></td>
        <td><strong>${d.name}</strong></td>
        <td style="font-weight:800; color:var(--primary); font-family:var(--font-mono);">
          ${d.discount_type === 'percentage' ? `${(d.value * 100).toFixed(0)}% OFF` : `$${d.value.toFixed(2)} OFF`}
        </td>
        <td><span class="badge badge-draft">${d.scope}</span></td>
        <td>${d.min_quantity > 0 ? `Min ${d.min_quantity} seats` : (d.min_purchase_amount > 0 ? `Min $${d.min_purchase_amount}` : 'None')}</td>
        <td style="color:var(--text-secondary); font-size:12px;">${d.start_date || 'Any'} &rarr; ${d.end_date || 'Any'}</td>
        <td>
          <strong>${d.times_used}</strong> / ${d.usage_limit > 0 ? d.usage_limit : 'Unlimited'}
        </td>
      </tr>
    `).join('');
  } catch (err) {
    console.error(err);
  }
}

// ======================== TAXES ========================

async function loadTaxes() {
  try {
    const taxes = await api('/api/taxes');
    STATE.taxes = taxes;
    const tbody = document.getElementById('table-taxes-body');
    tbody.innerHTML = taxes.map(t => `
      <tr>
        <td><strong>${t.name}</strong></td>
        <td class="tabular-nums" style="font-weight:800; font-family:var(--font-mono);">${(t.rate * 100).toFixed(1)}%</td>
        <td><span class="badge badge-active"><span class="status-dot"></span>Active</span></td>
      </tr>
    `).join('');
  } catch (err) {
    console.error(err);
  }
}

// ======================== STAFF (ADMIN ONLY) ========================

async function loadStaff() {
  try {
    const staff = await api('/api/staff');
    const tbody = document.getElementById('table-staff-body');
    tbody.innerHTML = staff.map(s => `
      <tr>
        <td><code>#${s.id}</code></td>
        <td><strong>${s.full_name}</strong></td>
        <td style="color:var(--text-secondary);">${s.email}</td>
        <td><span class="badge ${s.role === 'admin' ? 'badge-confirmed' : 'badge-quotation'}">${s.role}</span></td>
        <td style="color:var(--text-muted); font-size:12px;">${s.created_at}</td>
      </tr>
    `).join('');
  } catch (err) {
    console.error(err);
  }
}

// ======================== CUSTOMER PORTAL ========================

async function loadPortal() {
  try {
    const subs = await api('/api/subscriptions');
    const invs = await api('/api/invoices');

    const subsBody = document.getElementById('table-portal-subs-body');
    if (subs.length === 0) {
      subsBody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:24px; color:var(--text-muted);">No subscriptions found for your account.</td></tr>`;
    } else {
      subsBody.innerHTML = subs.map(s => `
        <tr>
          <td><strong style="font-family:var(--font-mono); color:var(--primary);">${s.subscription_number}</strong></td>
          <td>${s.plan_name} (${s.billing_frequency})</td>
          <td><span class="badge badge-${s.status}"><span class="status-dot"></span>${s.status}</span></td>
          <td>${s.start_date}</td>
          <td>${s.expiry_date || 'Ongoing'}</td>
          <td style="font-family:var(--font-mono);">${s.next_billing_date || '-'}</td>
          <td>
            ${s.status === 'active' && s.allow_pause ? `<button class="btn btn-outline btn-sm" onclick="advanceSubStatus(${s.id}, 'paused')">Pause</button>` : ''}
            ${s.status === 'paused' ? `<button class="btn btn-secondary btn-sm" onclick="advanceSubStatus(${s.id}, 'active')">Resume</button>` : ''}
          </td>
        </tr>
      `).join('');
    }

    const invsBody = document.getElementById('table-portal-invoices-body');
    if (invs.length === 0) {
      invsBody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:24px; color:var(--text-muted);">No invoices found.</td></tr>`;
    } else {
      invsBody.innerHTML = invs.map(i => `
        <tr>
          <td><strong style="font-family:var(--font-mono); color:var(--primary);">${i.invoice_number}</strong></td>
          <td>${i.issue_date}</td>
          <td>${i.due_date}</td>
          <td class="tabular-nums" style="font-weight:700; font-family:var(--font-mono);">$${i.total_amount.toFixed(2)}</td>
          <td class="tabular-nums" style="${i.balance_due > 0 ? 'color:var(--danger); font-weight:800; font-family:var(--font-mono);' : 'color:var(--success); font-weight:700;'}">$${i.balance_due.toFixed(2)}</td>
          <td><span class="badge badge-${i.status}"><span class="status-dot"></span>${i.status}</span></td>
          <td>
            <div style="display:flex; gap:6px;">
              <button class="btn btn-outline btn-sm" onclick="viewPrintInvoice(${i.id})">Print / PDF</button>
              ${i.balance_due > 0 ? `<button class="btn btn-primary btn-sm" onclick="openPaymentForInvoice(${i.id}, '${i.invoice_number}', ${i.balance_due}, '${i.customer_name}')">Pay Now</button>` : ''}
            </div>
          </td>
        </tr>
      `).join('');
    }
  } catch (err) {
    console.error(err);
  }
}

// ======================== MODAL CONTROLS ========================

function openModal(modalId) {
  const el = document.getElementById(modalId);
  if (el) el.classList.add('active');
}

function closeModal(modalId) {
  const el = document.getElementById(modalId);
  if (el) el.classList.remove('active');
}

// 1. Billing Modal
function openBillingModal() {
  const dateInput = document.getElementById('input-billing-date');
  dateInput.value = new Date().toISOString().split('T')[0];
  document.getElementById('billing-run-results').style.display = 'none';
  openModal('modal-billing');
}

async function executeBillingRun() {
  const asOf = document.getElementById('input-billing-date').value;
  const btn = document.getElementById('btn-execute-billing');
  btn.disabled = true;
  btn.innerText = 'Processing Billing Engine...';

  try {
    const res = await api('/api/billing/run', {
      method: 'POST',
      body: JSON.stringify({ as_of_date: asOf })
    });

    const resBox = document.getElementById('billing-run-results');
    resBox.style.display = 'block';
    resBox.innerHTML = `
      <div style="background:var(--success-light); border:1px solid var(--success-border); padding:16px; border-radius:var(--radius);">
        <h4 style="color:var(--success); margin-bottom:8px; display:flex; align-items:center; gap:6px;">
          <span>✅</span> Billing Batch Run Completed
        </h4>
        <div style="font-size:13px; line-height:1.6;">
          <div>• <strong>${res.created_count}</strong> new invoice(s) generated.</div>
          <div>• <strong>${res.skipped_count}</strong> already-billed subscription(s) skipped (Idempotency protected).</div>
          <div>• <strong>${res.auto_closed_count}</strong> expired subscription(s) auto-closed.</div>
        </div>
        ${res.invoices_created.length > 0 ? `
          <div style="margin-top:12px; font-size:12px; border-top:1px solid var(--success-border); padding-top:8px;">
            <strong>Generated Invoices:</strong>
            <ul style="padding-left:18px; margin-top:4px;">
              ${res.invoices_created.map(i => `<li><strong>${i.invoice_number}</strong> — ${i.customer_name} ($${i.total_amount.toFixed(2)})</li>`).join('')}
            </ul>
          </div>
        ` : ''}
      </div>
    `;

    showToast(`Billing complete! Created ${res.created_count} invoice(s).`, 'success');
    loadDashboard();
    loadInvoices();
    loadSubscriptions();
  } catch (err) {
    // handled
  } finally {
    btn.disabled = false;
    btn.innerText = 'Run Billing Now';
  }
}

// 2. Payment Modal
async function openPaymentModal() {
  await ensureInvoicesLoaded();
  const select = document.getElementById('pay-select-invoice');
  select.innerHTML = '<option value="">-- Choose an unpaid/confirmed invoice --</option>' +
    STATE.invoices.filter(i => i.balance_due > 0).map(i => `
      <option value="${i.id}" data-total="${i.total_amount}" data-balance="${i.balance_due}" data-customer="${i.customer_name}">
        ${i.invoice_number} - ${i.customer_name} (Balance: $${i.balance_due.toFixed(2)})
      </option>
    `).join('');

  document.getElementById('pay-invoice-details').style.display = 'none';
  document.getElementById('pay-amount').value = '';
  document.getElementById('pay-date').value = new Date().toISOString().split('T')[0];
  openModal('modal-payment');
}

function openPaymentForInvoice(invId, invNumber, balanceDue, customerName) {
  openPaymentModal().then(() => {
    const select = document.getElementById('pay-select-invoice');
    select.value = invId;
    onPaymentInvoiceSelected();
    document.getElementById('pay-amount').value = balanceDue;
  });
}

function onPaymentInvoiceSelected() {
  const select = document.getElementById('pay-select-invoice');
  const opt = select.selectedOptions[0];
  const box = document.getElementById('pay-invoice-details');

  if (!opt || !opt.value) {
    box.style.display = 'none';
    return;
  }

  box.style.display = 'block';
  document.getElementById('pay-detail-customer').innerText = opt.dataset.customer;
  document.getElementById('pay-detail-total').innerText = `$${parseFloat(opt.dataset.total).toFixed(2)}`;
  document.getElementById('pay-detail-balance').innerText = `$${parseFloat(opt.dataset.balance).toFixed(2)}`;
  document.getElementById('pay-amount').value = parseFloat(opt.dataset.balance).toFixed(2);
}

async function submitPayment() {
  const invId = document.getElementById('pay-select-invoice').value;
  const amount = parseFloat(document.getElementById('pay-amount').value || 0);
  const method = document.getElementById('pay-method').value;
  const payDate = document.getElementById('pay-date').value;
  const note = document.getElementById('pay-note').value;

  if (!invId) return showToast('Please select an invoice', 'error');
  if (amount <= 0) return showToast('Enter a valid payment amount', 'error');

  try {
    const res = await api('/api/payments', {
      method: 'POST',
      body: JSON.stringify({
        invoice_id: parseInt(invId),
        amount,
        payment_method: method,
        payment_date: payDate,
        note
      })
    });

    showToast(`Payment ${res.payment_number} recorded! Status: ${res.invoice_status.toUpperCase()}`, 'success');
    closeModal('modal-payment');
    loadDashboard();
    loadInvoices();
    loadPayments();
    if (STATE.currentPersona === 'customer') loadPortal();
  } catch (err) {}
}

// 3. Printable Invoice Sheet
async function viewPrintInvoice(invId) {
  try {
    const inv = await api(`/api/invoices/${invId}`);
    const sheet = document.getElementById('invoice-sheet-content');

    const linesHtml = inv.lines.map(l => `
      <tr>
        <td>
          <strong>${l.description}</strong>
        </td>
        <td class="tabular-nums">${l.quantity}</td>
        <td class="tabular-nums">$${l.unit_price.toFixed(2)}</td>
        <td class="tabular-nums">${(l.tax_rate * 100).toFixed(0)}% ($${l.tax_amount.toFixed(2)})</td>
        <td class="tabular-nums" style="text-align:right; font-weight:700;">$${l.total.toFixed(2)}</td>
      </tr>
    `).join('');

    sheet.innerHTML = `
      <div class="inv-header">
        <div>
          <div class="inv-company-name">Brightloop Software Inc.</div>
          <div style="font-size:12px; color:#64748b; margin-top:4px; line-height:1.5;">
            Enterprise Subscription & Revenue Platform<br>
            100 Innovation Way, Suite 400 &bull; San Francisco, CA 94107<br>
            billing@brightloop.com &bull; +1 (800) 555-LOOP
          </div>
        </div>
        <div style="text-align:right;">
          <h2 style="color:#4f46e5; font-size:24px; font-weight:800; letter-spacing:-0.03em;">TAX INVOICE</h2>
          <div style="font-size:15px; font-weight:700; font-family:monospace; margin-top:2px;">${inv.invoice_number}</div>
          <div style="font-size:12px; margin-top:4px;">
            Status: <span class="badge badge-${inv.status}" style="vertical-align:middle;">${inv.status}</span>
          </div>
        </div>
      </div>

      <div class="inv-details-grid">
        <div style="background:#f8fafc; padding:16px; border-radius:8px; border:1px solid #e2e8f0;">
          <div style="font-size:11px; text-transform:uppercase; color:#64748b; font-weight:700; letter-spacing:0.05em; margin-bottom:4px;">Billed To:</div>
          <div style="font-size:15px; font-weight:800; color:#0f172a;">${inv.customer_name}</div>
          <div style="color:#475569; font-weight:600;">${inv.company_name || ''}</div>
          <div style="color:#64748b; font-size:12px;">${inv.customer_email}</div>
        </div>
        <div style="background:#f8fafc; padding:16px; border-radius:8px; border:1px solid #e2e8f0; font-size:12.5px; line-height:1.7;">
          <div><strong>Issue Date:</strong> ${inv.issue_date}</div>
          <div><strong>Due Date:</strong> <span style="font-weight:700;">${inv.due_date}</span></div>
          <div><strong>Subscription:</strong> ${inv.subscription_number || 'N/A'}</div>
          <div><strong>Billing Period:</strong> ${inv.billing_period_start || ''} &mdash; ${inv.billing_period_end || ''}</div>
        </div>
      </div>

      <table class="data-table" style="margin-bottom:20px; border:1px solid #e2e8f0; border-radius:8px; overflow:hidden;">
        <thead>
          <tr style="background:#f1f5f9;">
            <th style="padding:10px 14px; color:#475569;">Item / Service Description</th>
            <th style="padding:10px 14px; color:#475569;">Qty</th>
            <th style="padding:10px 14px; color:#475569;">Unit Price</th>
            <th style="padding:10px 14px; color:#475569;">Taxes</th>
            <th style="padding:10px 14px; text-align:right; color:#475569;">Total</th>
          </tr>
        </thead>
        <tbody>
          ${linesHtml}
        </tbody>
      </table>

      <div class="inv-summary-box">
        <div class="inv-summary-row">
          <span>Subtotal:</span>
          <span class="tabular-nums" style="font-weight:600;">$${inv.subtotal.toFixed(2)}</span>
        </div>
        <div class="inv-summary-row">
          <span>Taxes:</span>
          <span class="tabular-nums">$${inv.tax_amount.toFixed(2)}</span>
        </div>
        ${inv.discount_amount > 0 ? `
          <div class="inv-summary-row" style="color:var(--accent); font-weight:700;">
            <span>Discount Applied:</span>
            <span class="tabular-nums">-$${inv.discount_amount.toFixed(2)}</span>
          </div>
        ` : ''}
        <div class="inv-summary-row total">
          <span>Total Amount:</span>
          <span class="tabular-nums" style="color:#4f46e5;">$${inv.total_amount.toFixed(2)}</span>
        </div>
        <div class="inv-summary-row" style="color:#059669; font-weight:600;">
          <span>Amount Paid:</span>
          <span class="tabular-nums">$${inv.amount_paid.toFixed(2)}</span>
        </div>
        <div class="inv-summary-row" style="color:#e11d48; font-weight:800; font-size:15px;">
          <span>Balance Due:</span>
          <span class="tabular-nums">$${inv.balance_due.toFixed(2)}</span>
        </div>
      </div>

      <div style="margin-top:28px; border-top:1px solid #e2e8f0; padding-top:16px; font-size:11.5px; color:#64748b; line-height:1.6;">
        <strong>Remittance & Bank Instructions:</strong> Wire transfer to Brightloop Software Inc., Silicon Valley Bank, Routing: 121000358, Account: 9948-2819-021. Please quote <strong>${inv.invoice_number}</strong> on all payments. Thank you for your business!
      </div>
    `;

    openModal('modal-invoice-print');
  } catch (err) {}
}

function printInvoice() {
  window.print();
}

// 4. New Subscription / Quote Modal
async function openNewSubscriptionModal() {
  await Promise.all([ensureCustomersLoaded(), ensureProductsLoaded(), ensurePlansLoaded()]);

  const custSelect = document.getElementById('sub-customer-select');
  custSelect.innerHTML = STATE.customers.map(c => `<option value="${c.id}">${c.full_name} (${c.company_name || c.email})</option>`).join('');

  const planSelect = document.getElementById('sub-plan-select');
  planSelect.innerHTML = STATE.plans.map(p => `<option value="${p.id}">${p.name} - $${p.base_price}/${p.billing_frequency}</option>`).join('');

  document.getElementById('sub-start-date').value = new Date().toISOString().split('T')[0];
  document.getElementById('sub-lines-container').innerHTML = '';
  addSubLineRow(); // Add initial line
  openModal('modal-new-sub');
}

function addSubLineRow() {
  const container = document.getElementById('sub-lines-container');
  const rowId = `line-row-${Date.now()}`;
  const row = document.createElement('div');
  row.className = 'form-row';
  row.id = rowId;
  row.style.alignItems = 'flex-end';
  row.style.marginBottom = '12px';

  const prodOptions = STATE.products.map(p => `<option value="${p.id}" data-price="${p.sales_price}">${p.name} ($${p.sales_price})</option>`).join('');

  row.innerHTML = `
    <div class="form-group" style="flex:2;">
      <label class="form-label">Product:</label>
      <select class="form-control prod-select" onchange="onSubLineProductChanged('${rowId}')">${prodOptions}</select>
    </div>
    <div class="form-group" style="flex:2;">
      <label class="form-label">Variant:</label>
      <select class="form-control variant-select" onchange="onSubLineVariantChanged('${rowId}')"></select>
    </div>
    <div class="form-group" style="flex:1;">
      <label class="form-label">Quantity:</label>
      <input type="number" class="form-control qty-input" value="1" min="1">
    </div>
    <div class="form-group" style="flex:1;">
      <label class="form-label">Unit Price ($):</label>
      <input type="number" step="0.01" class="form-control price-input" value="1200.00">
    </div>
    <button class="btn btn-outline btn-sm" style="margin-bottom:18px; color:var(--danger); border-color:var(--danger-border);" onclick="document.getElementById('${rowId}').remove()">&times;</button>
  `;

  container.appendChild(row);
  onSubLineProductChanged(rowId);
}

function onSubLineProductChanged(rowId) {
  const row = document.getElementById(rowId);
  const prodId = parseInt(row.querySelector('.prod-select').value);
  const prod = STATE.products.find(p => p.id === prodId);
  const varSelect = row.querySelector('.variant-select');

  if (prod && prod.variants && prod.variants.length > 0) {
    varSelect.innerHTML = prod.variants.map(v => `
      <option value="${v.id}" data-surcharge="${v.price_surcharge}">
        ${v.attribute_value} ${v.price_surcharge > 0 ? `(+$${v.price_surcharge})` : ''}
      </option>
    `).join('');
  } else {
    varSelect.innerHTML = '<option value="">Standard (No surcharge)</option>';
  }

  onSubLineVariantChanged(rowId);
}

function onSubLineVariantChanged(rowId) {
  const row = document.getElementById(rowId);
  const prodId = parseInt(row.querySelector('.prod-select').value);
  const prod = STATE.products.find(p => p.id === prodId);
  const varSelect = row.querySelector('.variant-select');
  const opt = varSelect.selectedOptions[0];
  const surcharge = opt ? parseFloat(opt.dataset.surcharge || 0) : 0;

  const basePrice = prod ? prod.sales_price : 0;
  const effectivePrice = basePrice + surcharge;
  row.querySelector('.price-input').value = effectivePrice.toFixed(2);
}

async function submitNewSubscription() {
  const customerId = parseInt(document.getElementById('sub-customer-select').value);
  const planId = parseInt(document.getElementById('sub-plan-select').value);
  const status = document.getElementById('sub-stage-select').value;
  const pTerms = document.getElementById('sub-terms-select').value;
  const startDate = document.getElementById('sub-start-date').value;
  const expiryDate = document.getElementById('sub-expiry-date').value || null;

  const lineRows = document.querySelectorAll('#sub-lines-container .form-row');
  const lines = [];

  lineRows.forEach(r => {
    const prodId = parseInt(r.querySelector('.prod-select').value);
    const varVal = r.querySelector('.variant-select').value;
    const varId = varVal ? parseInt(varVal) : null;
    const qty = parseInt(r.querySelector('.qty-input').value || 1);
    const unitPrice = parseFloat(r.querySelector('.price-input').value || 0);

    lines.push({
      product_id: prodId,
      variant_id: varId,
      quantity: qty,
      unit_price: unitPrice,
      tax_id: 1 // Default tax
    });
  });

  try {
    const res = await api('/api/subscriptions', {
      method: 'POST',
      body: JSON.stringify({
        customer_id: customerId,
        plan_id: planId,
        status,
        payment_terms: pTerms,
        start_date: startDate,
        expiry_date: expiryDate,
        lines
      })
    });

    showToast(`Subscription ${res.subscription_number} created successfully!`, 'success');
    closeModal('modal-new-sub');
    loadSubscriptions();
    loadDashboard();
  } catch (err) {}
}

// 5. Staff Modal (Admin only)
function openNewStaffModal() {
  document.getElementById('staff-name').value = '';
  document.getElementById('staff-email').value = '';
  document.getElementById('staff-password').value = '';
  checkStaffPassword('');
  openModal('modal-new-staff');
}

function checkStaffPassword(pwd) {
  updatePasswordChecklist(pwd, 'rule-len', 'rule-upper', 'rule-lower', 'rule-special', 'staff-pwd-meter');
}

function checkSignupPassword(pwd) {
  updatePasswordChecklist(pwd, 's-rule-len', 's-rule-upper', 's-rule-lower', 's-rule-special', 'signup-pwd-meter');
}

function updatePasswordChecklist(pwd, rLen, rUp, rLow, rSpec, meterId) {
  const lenOk = pwd.length > 8;
  const upOk = /[A-Z]/.test(pwd);
  const lowOk = /[a-z]/.test(pwd);
  const specOk = /[^A-Za-z0-9]/.test(pwd);

  setRuleStatus(rLen, lenOk, 'More than 8 characters (>8)');
  setRuleStatus(rUp, upOk, 'At least one uppercase letter (A-Z)');
  setRuleStatus(rLow, lowOk, 'At least one lowercase letter (a-z)');
  setRuleStatus(rSpec, specOk, 'At least one special character (!@#$%^&*)');

  // Update Dynamic Visual Meter
  if (meterId) {
    const meter = document.getElementById(meterId);
    if (meter) {
      const score = [lenOk, upOk, lowOk, specOk].filter(Boolean).length;
      const pct = (score / 4) * 100;
      meter.style.width = `${pct}%`;
      if (score <= 1) meter.style.backgroundColor = 'var(--danger)';
      else if (score === 2) meter.style.backgroundColor = 'var(--warning)';
      else if (score === 3) meter.style.backgroundColor = 'var(--secondary)';
      else if (score === 4) meter.style.backgroundColor = 'var(--success)';
    }
  }
}

function setRuleStatus(elId, valid, label) {
  const el = document.getElementById(elId);
  if (!el) return;
  if (valid) {
    el.innerHTML = `✅ ${label}`;
    el.classList.add('valid');
  } else {
    el.innerHTML = `⚪ ${label}`;
    el.classList.remove('valid');
  }
}

async function submitNewStaff() {
  const name = document.getElementById('staff-name').value;
  const email = document.getElementById('staff-email').value;
  const role = document.getElementById('staff-role').value;
  const password = document.getElementById('staff-password').value;

  try {
    const res = await api('/api/staff', {
      method: 'POST',
      body: JSON.stringify({ full_name: name, email, role, password })
    });
    showToast(res.message, 'success');
    closeModal('modal-new-staff');
    loadStaff();
  } catch (err) {}
}

// 6. Product Modal
function openNewProductModal() {
  openModal('modal-new-product');
}

async function submitNewProduct() {
  const name = document.getElementById('prod-name').value;
  const type = document.getElementById('prod-type').value;
  const salesPrice = parseFloat(document.getElementById('prod-sales-price').value || 0);
  const costPrice = parseFloat(document.getElementById('prod-cost-price').value || 0);
  const varAttr = document.getElementById('prod-variant-attr').value;
  const varVal = document.getElementById('prod-variant-val').value;
  const surcharge = parseFloat(document.getElementById('prod-variant-surcharge').value || 0);

  const variants = [];
  if (varAttr && varVal) {
    variants.push({ attribute_name: varAttr, attribute_value: varVal, price_surcharge: surcharge });
  }

  try {
    const res = await api('/api/products', {
      method: 'POST',
      body: JSON.stringify({ name, type, sales_price: salesPrice, cost_price: costPrice, variants })
    });
    showToast(res.message, 'success');
    closeModal('modal-new-product');
    loadProducts();
  } catch (err) {}
}

// 7. Plan Modal
function openNewPlanModal() {
  openModal('modal-new-plan');
}

async function submitNewPlan() {
  const name = document.getElementById('plan-name').value;
  const code = document.getElementById('plan-code').value;
  const basePrice = parseFloat(document.getElementById('plan-price').value || 0);
  const freq = document.getElementById('plan-freq').value;
  const minQ = parseInt(document.getElementById('plan-min-q').value || 1);
  const autoClose = document.getElementById('plan-auto-close').checked ? 1 : 0;
  const allowEarly = document.getElementById('plan-allow-early').checked ? 1 : 0;
  const allowPause = document.getElementById('plan-allow-pause').checked ? 1 : 0;
  const allowRenew = document.getElementById('plan-allow-renew').checked ? 1 : 0;

  try {
    const res = await api('/api/plans', {
      method: 'POST',
      body: JSON.stringify({
        name, code, base_price: basePrice, billing_frequency: freq, min_quantity: minQ,
        auto_close: autoClose, allow_close_early: allowEarly, allow_pause: allowPause, allow_renewal: allowRenew
      })
    });
    showToast(res.message, 'success');
    closeModal('modal-new-plan');
    loadPlans();
  } catch (err) {}
}

// 8. Discount Modal
function openNewDiscountModal() {
  openModal('modal-new-discount');
}

async function submitNewDiscount() {
  const code = document.getElementById('disc-code').value;
  const name = document.getElementById('disc-name').value;
  const dtype = document.getElementById('disc-type').value;
  const val = parseFloat(document.getElementById('disc-val').value || 0);
  const minQ = parseInt(document.getElementById('disc-min-q').value || 0);
  const minP = parseFloat(document.getElementById('disc-min-p').value || 0);
  const limit = parseInt(document.getElementById('disc-limit').value || 0);
  const scope = document.getElementById('disc-scope').value;

  try {
    const res = await api('/api/discounts', {
      method: 'POST',
      body: JSON.stringify({
        code, name, discount_type: dtype, value: val, min_quantity: minQ,
        min_purchase_amount: minP, usage_limit: limit, scope
      })
    });
    showToast(res.message, 'success');
    closeModal('modal-new-discount');
    loadDiscounts();
  } catch (err) {}
}

// 9. Customer Signup & Forgot Password Dialog
function openAuthModal() {
  openModal('modal-auth-dialog');
}

function toggleAuthTab(tab) {
  if (tab === 'signup') {
    document.getElementById('tab-auth-signup').classList.add('active');
    document.getElementById('tab-auth-forgot').classList.remove('active');
    document.getElementById('auth-signup-section').style.display = 'block';
    document.getElementById('auth-forgot-section').style.display = 'none';
  } else {
    document.getElementById('tab-auth-signup').classList.remove('active');
    document.getElementById('tab-auth-forgot').classList.add('active');
    document.getElementById('auth-signup-section').style.display = 'none';
    document.getElementById('auth-forgot-section').style.display = 'block';
  }
}

async function submitCustomerSignup() {
  const name = document.getElementById('signup-name').value;
  const comp = document.getElementById('signup-company').value;
  const email = document.getElementById('signup-email').value;
  const pwd = document.getElementById('signup-password').value;

  try {
    const res = await api('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ full_name: name, company_name: comp, email, password: pwd })
    });
    showToast(`Account created for ${res.user.full_name}! You are now registered.`, 'success');
    closeModal('modal-auth-dialog');
  } catch (err) {}
}

async function submitForgotPassword() {
  const email = document.getElementById('forgot-email').value;
  try {
    const res = await api('/api/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify({ email })
    });
    const box = document.getElementById('forgot-result-box');
    box.style.display = 'block';
    box.innerHTML = `
      <div style="color:var(--success); font-weight:700;">✅ Reset Link Dispatched</div>
      <div style="font-size:12px; margin-top:4px;">${res.message}</div>
      ${res.reset_link ? `<div style="font-size:11px; margin-top:6px; word-break:break-all;"><strong>Reset URL:</strong> <code>${res.reset_link}</code></div>` : ''}
    `;
    showToast('Reset link dispatched!', 'success');
  } catch (err) {}
}

// 10. High-End Subscription Details Inspector Modal
async function openSubscriptionDetails(subId) {
  try {
    const sub = await api(`/api/subscriptions/${subId}`);
    const modalBody = document.getElementById('sub-details-body');
    if (!modalBody) return;

    modalBody.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; padding-bottom:16px; border-bottom:1px solid var(--border-color);">
        <div>
          <h2 style="font-size:20px; font-weight:800; font-family:var(--font-mono); color:var(--primary);">${sub.subscription_number}</h2>
          <div style="font-size:13px; color:var(--text-secondary); margin-top:2px;">
            Customer: <strong>${sub.customer_name}</strong> &bull; ${sub.company_name || 'Individual'} (${sub.customer_email})
          </div>
        </div>
        <div>
          <span class="badge badge-${sub.status}">
            <span class="status-dot"></span>
            ${sub.status}
          </span>
        </div>
      </div>

      <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:14px; margin-bottom:20px;">
        <div style="background:var(--bg-subtle); padding:12px; border-radius:var(--radius); border:1px solid var(--border-color);">
          <div style="font-size:11px; font-weight:700; color:var(--text-muted); text-transform:uppercase;">Plan</div>
          <div style="font-weight:700; margin-top:2px;">${sub.plan_name}</div>
          <div style="font-size:11px; color:var(--secondary); text-transform:capitalize;">${sub.billing_frequency} ($${sub.base_price})</div>
        </div>
        <div style="background:var(--bg-subtle); padding:12px; border-radius:var(--radius); border:1px solid var(--border-color);">
          <div style="font-size:11px; font-weight:700; color:var(--text-muted); text-transform:uppercase;">Contract Dates</div>
          <div style="font-weight:700; margin-top:2px;">${sub.start_date}</div>
          <div style="font-size:11px; color:var(--text-muted);">Exp: ${sub.expiry_date || 'Ongoing'}</div>
        </div>
        <div style="background:var(--bg-subtle); padding:12px; border-radius:var(--radius); border:1px solid var(--border-color);">
          <div style="font-size:11px; font-weight:700; color:var(--text-muted); text-transform:uppercase;">Next Billing Date</div>
          <div style="font-weight:700; font-family:var(--font-mono); color:var(--primary); margin-top:2px;">${sub.next_billing_date || '-'}</div>
          <div style="font-size:11px; color:var(--text-muted);">Terms: ${sub.payment_terms || 'Net 30'}</div>
        </div>
      </div>

      <h4 style="font-size:13px; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; color:var(--text-muted); margin-bottom:8px;">
        Contracted Products & Surcharges
      </h4>
      <table class="data-table" style="margin-bottom:16px;">
        <thead>
          <tr>
            <th>Product</th>
            <th>Variant</th>
            <th>Qty</th>
            <th>Unit Price</th>
            <th style="text-align:right;">Subtotal</th>
          </tr>
        </thead>
        <tbody>
          ${sub.lines.map(l => `
            <tr>
              <td><strong>${l.product_name}</strong></td>
              <td>${l.attribute_value ? `<span class="badge badge-draft">${l.attribute_value}</span>` : '<span style="color:var(--text-muted);">Base</span>'}</td>
              <td class="tabular-nums">${l.quantity}</td>
              <td class="tabular-nums">$${parseFloat(l.unit_price).toFixed(2)}</td>
              <td class="tabular-nums" style="text-align:right; font-weight:700;">$${(l.quantity * l.unit_price).toFixed(2)}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;

    openModal('modal-sub-details');
  } catch (err) {}
}

// ======================== CACHE HELPERS ========================

async function ensureCustomersLoaded() {
  if (STATE.customers.length === 0) {
    STATE.customers = await api('/api/customers');
  }
}

async function ensureProductsLoaded() {
  if (STATE.products.length === 0) {
    STATE.products = await api('/api/products');
  }
}

async function ensurePlansLoaded() {
  if (STATE.plans.length === 0) {
    STATE.plans = await api('/api/plans');
  }
}

async function ensureInvoicesLoaded() {
  STATE.invoices = await api('/api/invoices');
}

// ======================== APP INIT ========================

window.addEventListener('DOMContentLoaded', () => {
  initTheme();
  loadDashboard();
  loadSubscriptions();
  loadInvoices();
});
