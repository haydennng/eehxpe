// ==================== Utility Functions ====================

// API call wrapper
async function api(url, options = {}) {
    console.log(`API: Fetching ${url}...`);
    console.log('API: Options:', options);
    
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        const method = options.method || 'GET';
        
        console.log(`API: Opening ${method} request...`);
        xhr.open(method, url, true);
        xhr.timeout = 5000; // 5 second timeout
        xhr.setRequestHeader('Content-Type', 'application/json');
        
        xhr.onload = function() {
            console.log(`API: Got response, status: ${xhr.status}`);
            try {
                const data = JSON.parse(xhr.responseText);
                console.log('API: Parsed JSON:', data);
                
                if (xhr.status >= 200 && xhr.status < 300) {
                    console.log('API: Success!');
                    resolve(data);
                } else {
                    console.error('API: Response not OK:', data);
                    reject(new Error(data.error || 'Request failed'));
                }
            } catch (e) {
                console.error('API: Failed to parse JSON:', e);
                reject(e);
            }
        };
        
        xhr.onerror = function() {
            console.error('API: Network error');
            reject(new Error('Network error'));
        };
        
        xhr.ontimeout = function() {
            console.error('API: Request timeout');
            reject(new Error('Request timeout'));
        };
        
        console.log('API: Sending request...');
        if (options.body) {
            console.log('API: Request body:', options.body);
            xhr.send(options.body);
        } else {
            xhr.send();
        }
        console.log('API: Request sent!');
    });
}

// Selector shortcuts
const qs = (selector) => document.querySelector(selector);
const qsa = (selector) => document.querySelectorAll(selector);

// Toast notification
function toast(message, type = 'success') {
    const container = qs('#toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Format date/time
function formatDateTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleString();
}

function formatTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// Format currency
function formatCurrency(amount) {
    return `$${Number(amount).toFixed(2)}`;
}

// Format earnings with sign and color class
function formatEarnings(amount) {
    const absAmount = Math.abs(Number(amount));
    const formatted = absAmount.toFixed(2);
    
    if (amount > 0) {
        return { text: `+$${formatted}`, className: 'text-success' };
    } else if (amount < 0) {
        return { text: `-$${formatted}`, className: 'text-danger' };
    } else {
        return { text: `$${formatted}`, className: '' };
    }
}

// Format date
function formatDate(dateStr) {
    const date = new Date(dateStr + 'T00:00:00');
    return date.toLocaleDateString('en-US', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' });
}

// Format signed integer (for player pills showing earnings)
function formatSignedInt(value) {
    const n = Math.round(Number(value) || 0);
    if (n > 0) return '+' + n;
    if (n < 0) return String(n);
    return '0';
}

// Format date with design component (date-design)
function formatDateDesign(dateStr) {
    try {
        // Parse date robustly to avoid timezone drift
        let date;
        if (typeof dateStr === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
            // YYYY-MM-DD format - construct local date
            const [year, month, day] = dateStr.split('-').map(Number);
            date = new Date(year, month - 1, day);
        } else {
            // Fallback to standard parsing
            date = new Date(dateStr);
        }
        
        // Validate date
        if (isNaN(date.getTime())) {
            return escapeHtml(dateStr || '—');
        }
        
        // Format as yyyy:mm:dd
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const formattedDate = `${year}:${month}:${day}`;
        
        // Get 3-letter day abbreviation
        const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        const dow = days[date.getDay()];
        
        // Build aria label for accessibility (e.g., "Sun 2025-10-26")
        const ariaLabel = `${dow} ${year}-${month}-${day}`;
        
        // Return HTML component with day-of-week above date
        return `<div class="date-design" role="group" aria-label="${ariaLabel}">
            <div class="date-design__dow">${dow}</div>
            <div class="date-design__date">
                <span class="date-design__year">${year}</span> <span class="date-design__month">${month}</span> <span class="date-design__day">${day}</span>
            </div>
        </div>`;
    } catch (error) {
        console.error('formatDateDesign error:', error);
        return escapeHtml(dateStr || '—');
    }
}

// ==================== Dashboard Page ====================

async function initDashboard() {
    await loadDashboardStats();
    await loadMonthlyEarnings();
}

async function loadDashboardStats() {
    try {
        // Get session info
        const session = await api('/api/session');
        qs('#playerCount').textContent = session.player_count;
        
        // Get match count
        const matches = await api('/api/matches');
        qs('#matchCount').textContent = matches.length;
        
        // Get sessions count
        const sessions = await api('/api/sessions');
        qs('#sessionsCount').textContent = sessions.length;
        
        // Load quick recap
        await loadQuickRecap(sessions);
    } catch (error) {
        console.error('Failed to load dashboard stats', error);
    }
}

async function loadMonthlyEarnings() {
    try {
        // Get current month name
        const now = new Date();
        const monthName = now.toLocaleString('en-US', { month: 'long' });
        
        // Update header with month name - changed to "Stats"
        const header = qs('#monthlyEarningsHeader');
        if (header) {
            header.textContent = `${monthName} Stats`;
        }
        
        // Get earnings data, players data, and monthly matches for MMR calculation
        const [earnings, players, stats] = await Promise.all([
            api('/api/earnings/monthly'),
            api('/api/players'),
            api('/api/stats')
        ]);
        
        const container = qs('#monthlyEarningsList');
        
        if (!container) {
            console.error('Monthly earnings container not found');
            return;
        }
        
        if (earnings.length === 0) {
            container.innerHTML = '<div style="color: var(--text-muted); font-size: 0.875rem; padding: 1rem;">No stats data yet</div>';
            return;
        }
        
        // Create MMR lookup map and calculate MMR changes
        const mmrMap = {};
        const statsMap = {};
        
        players.forEach(p => {
            const name = typeof p === 'string' ? p : p.name;
            const mmr = (typeof p === 'object' && p.mmr) ? p.mmr : 1500;
            mmrMap[name] = mmr;
        });
        
        stats.forEach(s => {
            statsMap[s.player] = {
                totalMatches: s.total_matches || 0,
                mmr: s.mmr || 1500
            };
        });
        
        // Calculate MMR change based on monthly performance
        // For simplicity, we'll estimate based on win rate vs expected
        const earningsWithMMR = earnings.map(player => {
            const winRate = player.games_played > 0 ? (player.games_played - (player.total_losses || 0)) / player.games_played : 0.5;
            const currentMMR = mmrMap[player.player] || 1500;
            
            // Estimate MMR gained/lost: roughly 24 points per game * win_rate_diff * games
            // Positive if winning more than 50%, negative if less
            const expectedWinRate = 0.5;
            const mmrChange = Math.round((winRate - expectedWinRate) * 24 * player.games_played);
            
            return {
                ...player,
                currentMMR,
                mmrChange
            };
        });
        
        // Build earnings display with MMR change
        const earningsHtml = earningsWithMMR.map(player => {
            const earningsFormatted = formatEarnings(player.net_earnings);
            const mmrChangeClass = player.mmrChange > 0 ? 'text-success' : (player.mmrChange < 0 ? 'text-danger' : 'text-muted');
            const mmrChangeSign = player.mmrChange > 0 ? '+' : '';
            const mmrChangeText = player.mmrChange !== 0 ? `${mmrChangeSign}${player.mmrChange}` : '—';
            
            return `
                <div class="earnings-item">
                    <span class="earnings-player">
                        <span class="mmr-badge">${Math.round(player.currentMMR)}</span>
                        <span class="player-name-text">${escapeHtml(player.player)}</span>
                        <span class="mmr-change ${mmrChangeClass}">${mmrChangeText}</span>
                    </span>
                    <span>
                        <span class="earnings-amount ${earningsFormatted.className}">${earningsFormatted.text}</span>
                        <span class="earnings-games">(${player.games_played})</span>
                    </span>
                </div>
            `;
        }).join('');
        
        container.innerHTML = earningsHtml;
    } catch (error) {
        console.error('Failed to load monthly earnings:', error);
        const container = qs('#monthlyEarningsList');
        if (container) {
            container.innerHTML = '<div style="color: var(--text-muted); font-size: 0.875rem; padding: 1rem;">Unable to load stats</div>';
        }
    }
}

// Helper: Get today's date as YYYY-MM-DD in local timezone
function getTodayLocalDate() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

// Helper: Get most recent session excluding today
function getMostRecentNonTodaySession(sessions) {
    const today = getTodayLocalDate();
    const pastSessions = sessions.filter(s => s.date < today);
    
    if (pastSessions.length === 0) return null;
    
    // Sort by date descending and return first
    pastSessions.sort((a, b) => b.date.localeCompare(a.date));
    return pastSessions[0];
}

// Helper: Categorize player performance
function categorizePlayerPerformance(netEarnings, winRate) {
    const hasPositiveEarnings = netEarnings > 0;
    const hasGoodWinRate = winRate > 0.5;
    
    if (hasPositiveEarnings && hasGoodWinRate) return 'green';
    if (hasPositiveEarnings || hasGoodWinRate) return 'orange';
    return 'red';
}

// Helper: Compute player win stats from matches
function computePlayerWinStats(matches) {
    const stats = {};
    
    matches.forEach(match => {
        const winners = match.winner === 'team1' ? match.team1 : match.team2;
        const losers = match.winner === 'team1' ? match.team2 : match.team1;
        
        // Track wins
        winners.forEach(player => {
            if (!stats[player]) stats[player] = { wins: 0, total: 0 };
            stats[player].wins++;
            stats[player].total++;
        });
        
        // Track losses
        losers.forEach(player => {
            if (!stats[player]) stats[player] = { wins: 0, total: 0 };
            stats[player].total++;
        });
    });
    
    return stats;
}

// Load quick recap of last 3 sessions (excluding today)
async function loadQuickRecap(sessions) {
    const tbody = qs('#quickRecapTableBody');
    
    try {
        // Get today's date as YYYY-MM-DD
        const today = getTodayLocalDate();
        
        // Filter out today's session and sort by date descending
        const pastSessions = sessions.filter(s => s.date < today);
        pastSessions.sort((a, b) => b.date.localeCompare(a.date));
        
        // Take the last 3 sessions
        const last3Sessions = pastSessions.slice(0, 3);
        
        if (last3Sessions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" class="table-empty">No previous sessions found</td></tr>';
            return;
        }
        
        // Fetch earnings data for all 3 sessions
        const sessionDataPromises = last3Sessions.map(async session => {
            const earningsData = await api(`/api/sessions/${session.session_id}/earnings`);
            return {
                session,
                players: earningsData.players || []
            };
        });
        
        const sessionsData = await Promise.all(sessionDataPromises);
        
        // Build table rows for each session
        const rowsHtml = sessionsData.map(({ session, players }) => {
            // Sort players by net_earnings descending
            players.sort((a, b) => b.net_earnings - a.net_earnings);
            
            // Build pills with earnings
            const pillsHtml = players.map(p => {
                const earningsStr = formatSignedInt(p.net_earnings);
                // Determine pill color based on earnings
                let pillClass = 'player-pill--neutral';
                if (p.net_earnings > 0) {
                    pillClass = 'player-pill--green';
                } else if (p.net_earnings < 0) {
                    pillClass = 'player-pill--red';
                }
                // else stays neutral (grey) for 0 earnings
                
                return `<span class="player-pill ${pillClass}">${escapeHtml(p.player)} ${earningsStr}</span>`;
            }).join('');
            
            // Calculate player average: sum of games each player played / number of players
            const totalGames = session.match_count || 0;
            const numberOfPlayers = players.length;
            // Sum up games_played for all players, then divide by number of players
            const totalGamesPlayed = players.reduce((sum, p) => sum + (p.games_played || 0), 0);
            const playerAverage = numberOfPlayers > 0 ? Math.round(totalGamesPlayed / numberOfPlayers) : 0;
            
            // Check if mobile (viewport width <= 768px)
            const isMobile = window.innerWidth <= 768;
            
            // Format games column: in mobile, combine avg and total with bullet
            const gamesDisplay = isMobile ? `${playerAverage} \u2022 ${totalGames}` : `${playerAverage} \u2022 ${totalGames}`;
            
            return `
                <tr>
                    <td>${formatDateDesign(session.date)}</td>
                    <td>
                        <div class="player-pills-container">
                            ${pillsHtml || '<span style="color: var(--text-muted);">No player data</span>'}
                        </div>
                    </td>
                    <td style="text-align: center;">${gamesDisplay}</td>
                </tr>
            `;
        }).join('');
        
        tbody.innerHTML = rowsHtml;
    } catch (error) {
        console.error('Failed to load quick recap:', error);
        tbody.innerHTML = '<tr><td colspan="3" class="table-empty">Unable to load recap</td></tr>';
    }
}

// ==================== Players Page ====================

async function initPlayers() {
    await loadPlayers();
    
    // Add player form
    qs('#addPlayerForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const name = qs('#playerName').value.trim();
        
        if (!name) {
            toast('Player name cannot be empty', 'error');
            return;
        }
        
        try {
            await api('/api/players', {
                method: 'POST',
                body: JSON.stringify({ name })
            });
            
            toast(`Added player: ${name}`);
            qs('#playerName').value = '';
            await loadPlayers();
        } catch (error) {
            toast(error.message, 'error');
        }
    });
}

async function loadPlayers() {
    try {
        const players = await api('/api/players');
        const tbody = qs('#playersTableBody');
        
        if (players.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" class="table-empty">No players added yet</td></tr>';
            return;
        }
        
        // Sort players by MMR descending (highest first)
        const sortedPlayers = players.sort((a, b) => {
            const mmrA = (typeof a === 'object' && a.mmr) ? a.mmr : 1500;
            const mmrB = (typeof b === 'object' && b.mmr) ? b.mmr : 1500;
            return mmrB - mmrA;
        });
        
        tbody.innerHTML = sortedPlayers.map(player => {
            // Handle both old string format and new object format
            const playerName = typeof player === 'string' ? player : player.name;
            const mmr = (typeof player === 'object' && player.mmr) ? player.mmr : 1500;
            return `
                <tr>
                    <td>${escapeHtml(playerName)}</td>
                    <td style="text-align: center;">${mmr}</td>
                    <td style="text-align: right;">
                        <button class="btn btn-danger btn-small" onclick="deletePlayer('${escapeHtml(playerName)}')">
                            Delete
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        toast('Failed to load players', 'error');
    }
}

async function deletePlayer(name) {
    if (!confirm(`Are you sure you want to remove ${name}?`)) {
        return;
    }
    
    try {
        await api(`/api/players/${encodeURIComponent(name)}`, {
            method: 'DELETE'
        });
        
        toast(`Removed player: ${name}`);
        await loadPlayers();
    } catch (error) {
        toast(error.message, 'error');
    }
}

// ==================== Matchups Page ====================

// Player selection and bet state
let selectedPlayers = [];
let selectedBet = null;
let lastSelectedBet = null; // Remember the last bet for the next match
let allPlayers = [];
let currentSession = null;

// Recommendation state (legacy single-court)
let currentRecommendation = null;
let allRecommendations = [];
let recommendationIndex = 0;

// Dual-court state
let isDualCourt = false;
let currentCourts = []; // [{court:1, team_a:[...], team_b:[...]}, ...]
let currentRecommendedIds = []; // 4 or 8 player names in court order
let activePlayersCount = 0; // Track active player count

async function initMatchups() {
    try {
        console.log('Starting matchups page initialization...');
        
        // Load current session first
        console.log('Loading current session...');
        currentSession = await api('/api/sessions/current');
        console.log('Current session loaded:', currentSession);
        
        console.log('Updating session display...');
        updateSessionDisplay();
        console.log('Session display updated');
        
        console.log('Loading players...');
        await loadPlayersForMatchups();
        console.log('Players loaded');
        
        console.log('Loading match history...');
        await loadMatchHistory();
        console.log('Match history loaded');
        
        console.log('Loading session stats...');
        await loadSessionStats();
        console.log('Session stats loaded');
        
        console.log('Loading player earnings...');
        await loadPlayerEarnings();
        console.log('Player earnings loaded');
        
        // Set up bet button handlers
        const betButtons = qsa('.btn-bet');
        if (betButtons.length === 0) {
            console.error('No bet buttons found');
            return;
        }
        
        betButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                qsa('.btn-bet').forEach(b => b.classList.remove('selected'));
                btn.classList.add('selected');
                selectedBet = parseInt(btn.dataset.value);
                lastSelectedBet = selectedBet; // Remember this bet for next time
                btn.setAttribute('aria-pressed', 'true');
                qsa('.btn-bet').forEach(b => {
                    if (b !== btn) b.setAttribute('aria-pressed', 'false');
                });
                validateForm();
            });
        });
        
        // Restore last selected bet if available
        if (lastSelectedBet !== null) {
            const lastBetButton = Array.from(betButtons).find(btn => parseInt(btn.dataset.value) === lastSelectedBet);
            if (lastBetButton) {
                lastBetButton.classList.add('selected');
                lastBetButton.setAttribute('aria-pressed', 'true');
                selectedBet = lastSelectedBet;
            }
        }
        
        // Set up score input handlers for both courts
        const court1ScoreA = qs('#court1-score-a');
        const court1ScoreB = qs('#court1-score-b');
        const court2ScoreA = qs('#court2-score-a');
        const court2ScoreB = qs('#court2-score-b');
        
        if (court1ScoreA && court1ScoreB) {
            court1ScoreA.addEventListener('input', validateForm);
            court1ScoreB.addEventListener('input', validateForm);
        } else {
            console.warn('Court 1 score inputs not found - this may affect form validation');
        }
        
        if (court2ScoreA && court2ScoreB) {
            court2ScoreA.addEventListener('input', validateForm);
            court2ScoreB.addEventListener('input', validateForm);
        }
        
        // Set up record match button
        const recordBtn = qs('#recordMatchBtn');
        if (!recordBtn) {
            console.error('Record match button not found');
            return;
        }
        
        recordBtn.addEventListener('click', async () => {
            try {
                await handleRecordMatch();
            } catch (err) {
                console.error('Button click error:', err);
                toast('An error occurred', 'error');
            }
        });
        
        // Set up unified recommendation/cycle button handler
        const cycleBtn = qs('#btn-cycle-recommendation');
        if (cycleBtn) {
        cycleBtn.addEventListener('click', async () => {
            console.log('Cycle button clicked. Selected players:', selectedPlayers.length);
            console.log('isDualCourt:', isDualCourt);
            console.log('activePlayersCount:', activePlayersCount);
            console.log('allRecommendations:', allRecommendations);
            
            // If no players selected, pick the current recommended matchup
            if (selectedPlayers.length === 0) {
                console.log('No players selected, setting recommended matchup');
                setRecommendedMatchup();
            } else {
                // For dual-court mode (8+ players): clear selection and get fresh recommendation
                if (isDualCourt) {
                    console.log('Dual-court mode - clearing and getting fresh recommendation');
                    selectedPlayers = [];
                    qsa('.player-name-btn').forEach(btn => {
                        btn.classList.remove('selected', 'team-a', 'team-b', 'court-1', 'court-2');
                        btn.setAttribute('aria-pressed', 'false');
                    });
                    updatePlayerButtonStates();
                    updateTeamPreview();
                    await cycleRecommendation();
                    setRecommendedMatchup();
                    return;
                }
                
                // If players are selected, cycle to next recommendation and auto-select them
                console.log('Players selected, cycling recommendation');
                await cycleRecommendation();
                console.log('After cycleRecommendation, calling setRecommendedMatchup');
                setRecommendedMatchup();
            }
        });
        }
        
        // Set up clear selected players button handler
        const clearBtn = qs('#btn-clear-selected');
        if (clearBtn) {
            clearBtn.addEventListener('click', clearSelectedPlayers);
        }
        
        // Set up resize handler to re-render match history on breakpoint change
        let lastIsMobile = window.matchMedia('(max-width: 768px)').matches;
        let resizeTimeout = null;
        
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                const currentIsMobile = window.matchMedia('(max-width: 768px)').matches;
                if (currentIsMobile !== lastIsMobile) {
                    lastIsMobile = currentIsMobile;
                    loadMatchHistory();
                }
            }, 250);
        });
        
        console.log('Matchups page initialized successfully');
    } catch (error) {
        console.error('Error initializing matchups page:', error);
        toast('Failed to initialize page', 'error');
    }
}

async function loadPlayersForMatchups() {
    try {
        console.log('loadPlayersForMatchups: Fetching players...');
        allPlayers = await api('/api/players');
        console.log('loadPlayersForMatchups: Got players:', allPlayers);
        
        // Count active players for dual-court mode
        activePlayersCount = allPlayers.filter(p => {
            const isActive = typeof p === 'string' ? true : (p.active !== undefined ? p.active : true);
            return isActive;
        }).length;
        console.log('loadPlayersForMatchups: Active players count:', activePlayersCount);
        
        // Force hide Court 2 if we have fewer than 8 active players
        if (activePlayersCount < 8) {
            const court2Row = qs('#court-2-row');
            const court1Number = qs('#court-1-number');
            const court2Number = qs('#court-2-number');
            const court2TeamA = qs('#court2-teamA');
            const court2TeamB = qs('#court2-teamB');
            
            if (court2Row) court2Row.hidden = true;
            if (court1Number) court1Number.hidden = true;
            if (court2Number) court2Number.hidden = true;
            if (court2TeamA) court2TeamA.textContent = '';
            if (court2TeamB) court2TeamB.textContent = '';
        }
        
        const container = qs('#playerToggles');
        if (!container) {
            console.error('loadPlayersForMatchups: #playerToggles container not found!');
            return;
        }
        
        if (allPlayers.length === 0) {
            container.innerHTML = '<div class="table-empty">No players added yet. Add players first.</div>';
            return;
        }
        
        // Render players with new two-button layout
        renderPlayers();
        
        console.log('loadPlayersForMatchups: Players rendered successfully');
        
        // Load recommendations after players are rendered
        await loadRecommendations();
    } catch (error) {
        console.error('loadPlayersForMatchups ERROR:', error);
        toast('Failed to load players', 'error');
    }
}

function renderPlayers() {
    const container = qs('#playerToggles');
    if (!container) return;
    
    // Sort players: active first, then alphabetically
    const sortedPlayers = [...allPlayers].sort((a, b) => {
        const aActive = a.active !== undefined ? a.active : true;
        const bActive = b.active !== undefined ? b.active : true;
        
        // Active players come first (true=1, false=0, so b-a puts true first)
        if (bActive !== aActive) return bActive - aActive;
        
        // Then alphabetically
        const aName = typeof a === 'string' ? a : a.name;
        const bName = typeof b === 'string' ? b : b.name;
        return aName.localeCompare(bName);
    });
    
    // Set grid columns based on player count
    if (sortedPlayers.length <= 9) {
        container.classList.remove('player-toggle-grid--4col');
        container.classList.add('player-toggle-grid--3col');
    } else {
        container.classList.remove('player-toggle-grid--3col');
        container.classList.add('player-toggle-grid--4col');
    }
    
    // Render player items with two buttons
    container.innerHTML = sortedPlayers.map(player => {
        const playerName = typeof player === 'string' ? player : player.name;
        const isActive = typeof player === 'string' ? true : (player.active !== undefined ? player.active : true);
        const toggleIcon = isActive ? '✓' : 'X';
        const containerClass = isActive ? 'player-item' : 'player-item is-deactivated';
        const disabledAttr = isActive ? '' : 'disabled';
        const ariaLabel = isActive ? `Deactivate ${playerName}` : `Activate ${playerName}`;
        const ariaPressed = isActive ? 'false' : 'true';
        
        return `
            <div class="${containerClass}" data-player="${escapeHtml(playerName)}">
                <button 
                    type="button" 
                    class="player-name-btn" 
                    data-player="${escapeHtml(playerName)}"
                    aria-pressed="false"
                    ${disabledAttr}
                >
                    ${escapeHtml(playerName)}
                </button>
                <button 
                    type="button" 
                    class="player-toggle-btn" 
                    data-player="${escapeHtml(playerName)}"
                    aria-pressed="${ariaPressed}"
                    aria-label="${ariaLabel}"
                    title="${ariaLabel}"
                >
                    ${toggleIcon}
                </button>
            </div>
        `;
    }).join('');
    
    // Add click handlers for name buttons
    qsa('.player-name-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            if (!btn.disabled) {
                togglePlayerSelection(btn);
            }
        });
    });
    
    // Add click handlers for toggle buttons
    qsa('.player-toggle-btn').forEach(btn => {
        btn.addEventListener('click', () => togglePlayerActive(btn.dataset.player));
    });
}

// Toggle player selection (name button click)
function togglePlayerSelection(btn) {
    const player = btn.dataset.player;
    const isSelected = selectedPlayers.includes(player);
    
    // Determine max selections based on active player count
    const maxSelected = activePlayersCount >= 8 ? 8 : 4;
    
    if (isSelected) {
        // Deselect
        selectedPlayers = selectedPlayers.filter(p => p !== player);
        btn.classList.remove('selected', 'court-1', 'court-2');
        btn.setAttribute('aria-pressed', 'false');
    } else {
        // Select (if less than max selected)
        if (selectedPlayers.length < maxSelected) {
            selectedPlayers.push(player);
            btn.classList.add('selected');
            btn.setAttribute('aria-pressed', 'true');
        }
    }
    
    // Apply court watermarks based on selection order
    applyCourtWatermarksToSelection();
    
    // Update disabled states and clear button
    updatePlayerButtonStates();
    
    // Update team colors
    updateTeamColors();
    updateTeamPreview();
    validateForm();
}

// Apply court watermarks to selected players based on their order
function applyCourtWatermarksToSelection() {
    // Remove all court classes first
    qsa('.player-name-btn').forEach(btn => {
        btn.classList.remove('court-1', 'court-2');
    });
    
    // Apply court classes based on selection order
    selectedPlayers.forEach((player, index) => {
        const btn = Array.from(qsa('.player-name-btn')).find(b => b.dataset.player === player);
        if (btn) {
            // Indices 0-3 = Court 1, 4-7 = Court 2
            if (index < 4) {
                btn.classList.add('court-1');
            } else if (index < 8) {
                btn.classList.add('court-2');
            }
        }
    });
}

// Legacy support for old single-button format
function togglePlayer(btn) {
    togglePlayerSelection(btn);
}

// Toggle player active/deactivated status (toggle button click)
async function togglePlayerActive(playerName) {
    console.log('togglePlayerActive called for:', playerName);
    
    // Find player in allPlayers
    const player = allPlayers.find(p => {
        const name = typeof p === 'string' ? p : p.name;
        return name === playerName;
    });
    
    if (!player) {
        console.error('Player not found:', playerName);
        return;
    }
    
    // Toggle active state (optimistic update)
    const wasActive = typeof player === 'string' ? true : (player.active !== undefined ? player.active : true);
    const newActive = !wasActive;
    
    // Update in-memory state
    if (typeof player === 'object') {
        player.active = newActive;
    }
    
    // If player was just deactivated and is currently selected, remove from selection
    if (!newActive && selectedPlayers.includes(playerName)) {
        console.log('Player deactivated while selected, removing from selection');
        selectedPlayers = selectedPlayers.filter(p => p !== playerName);
        
        // Try to auto-fill with recommendations
        await ensureSelectionCount();
    }
    
    // Recalculate active players count
    activePlayersCount = allPlayers.filter(p => {
        const isActive = typeof p === 'string' ? true : (p.active !== undefined ? p.active : true);
        return isActive;
    }).length;
    console.log('Updated activePlayersCount:', activePlayersCount);
    
    // If we now have fewer than 8 active players, clear all selections
    // This prevents invalid state where Court 2 shows with <8 active players
    if (activePlayersCount < 8 && selectedPlayers.length > 4) {
        console.log('Less than 8 active players, clearing excess selections');
        selectedPlayers = [];
        qsa('.player-name-btn').forEach(btn => {
            btn.classList.remove('selected', 'team-a', 'team-b', 'court-1', 'court-2');
            btn.setAttribute('aria-pressed', 'false');
        });
    }
    
    // Re-render players (this will move deactivated to bottom)
    renderPlayers();
    
    // Update team preview and validation (this will hide Court 2 if needed)
    updateTeamColors();
    updateTeamPreview();
    validateForm();
    
    // Persist to backend
    try {
        await api(`/api/players/${encodeURIComponent(playerName)}/active`, {
            method: 'PATCH',
            body: JSON.stringify({ active: newActive })
        });
        console.log('Player active status saved successfully');
        
        // Reload recommendations since active players changed
        await loadRecommendations();
    } catch (error) {
        console.error('Failed to save player active status:', error);
        toast('Failed to update player status', 'error');
        
        // Revert state on error
        if (typeof player === 'object') {
            player.active = wasActive;
        }
        
        // Re-render to show correct state
        renderPlayers();
        updateTeamColors();
        updateTeamPreview();
        validateForm();
    }
}

// Ensure we have up to 4 selected players by auto-filling from recommendations
async function ensureSelectionCount() {
    console.log('ensureSelectionCount: current selection:', selectedPlayers.length);
    
    // Get active players only
    const activePlayers = allPlayers.filter(p => {
        const isActive = typeof p === 'string' ? true : (p.active !== undefined ? p.active : true);
        return isActive;
    });
    
    console.log('ensureSelectionCount: active players:', activePlayers.length);
    
    // If we have less than 4 selected and there are available players
    while (selectedPlayers.length < 4 && selectedPlayers.length < activePlayers.length) {
        // Get next recommended player
        const nextPlayer = getNextRecommendedPlayer();
        
        if (!nextPlayer) {
            console.log('ensureSelectionCount: no more recommendations available');
            break;
        }
        
        console.log('ensureSelectionCount: auto-selecting', nextPlayer);
        selectedPlayers.push(nextPlayer);
    }
    
    // Re-apply selection UI
    qsa('.player-name-btn').forEach(btn => {
        const playerName = btn.dataset.player;
        if (selectedPlayers.includes(playerName)) {
            btn.classList.add('selected');
            btn.setAttribute('aria-pressed', 'true');
        } else {
            btn.classList.remove('selected');
            btn.setAttribute('aria-pressed', 'false');
        }
    });
    
    updatePlayerButtonStates();
    updateTeamColors();
    updateTeamPreview();
    validateForm();
}

// Get next recommended player that isn't already selected or inactive
function getNextRecommendedPlayer() {
    if (!currentRecommendation) return null;
    
    // Get all players from current recommendation
    const recommendedPlayers = [
        ...currentRecommendation.teamA,
        ...currentRecommendation.teamB
    ];
    
    // Find first player not already selected and is active
    for (const playerName of recommendedPlayers) {
        if (selectedPlayers.includes(playerName)) continue;
        
        // Check if player is active
        const player = allPlayers.find(p => {
            const name = typeof p === 'string' ? p : p.name;
            return name === playerName;
        });
        
        if (!player) continue;
        
        const isActive = typeof player === 'string' ? true : (player.active !== undefined ? player.active : true);
        if (isActive) {
            return playerName;
        }
    }
    
    return null;
}

function updatePlayerButtonStates() {
    const clearBtn = qs('#btn-clear-selected');
    
    // Enable/disable clear button based on selection
    if (clearBtn) {
        clearBtn.disabled = selectedPlayers.length === 0;
    }
    
    // Determine max selections based on active player count
    const maxSelected = activePlayersCount >= 8 ? 8 : 4;
    
    // Update disabled states for player buttons (name buttons)
    // Inactive players are already disabled via renderPlayers()
    if (selectedPlayers.length >= maxSelected) {
        qsa('.player-name-btn').forEach(b => {
            if (!b.classList.contains('selected') && !b.disabled) {
                b.disabled = true;
                b.setAttribute('data-temp-disabled', 'true');
            }
        });
    } else {
        qsa('.player-name-btn').forEach(b => {
            // Only re-enable if it was temporarily disabled (not permanently disabled due to inactive status)
            if (b.getAttribute('data-temp-disabled') === 'true') {
                b.disabled = false;
                b.removeAttribute('data-temp-disabled');
            }
        });
    }
    
    // Legacy support for old single-button format
    if (selectedPlayers.length >= maxSelected) {
        qsa('.btn-player-toggle').forEach(b => {
            if (!b.classList.contains('selected')) {
                b.disabled = true;
            }
        });
    } else {
        qsa('.btn-player-toggle').forEach(b => {
            b.disabled = false;
        });
    }
}

function clearSelectedPlayers() {
    // Clear player selection
    selectedPlayers = [];
    
    // Clear selection from name buttons
    qsa('.player-name-btn').forEach(btn => {
        btn.classList.remove('selected', 'team-a', 'team-b');
        btn.setAttribute('aria-pressed', 'false');
        // Don't modify disabled state here - renderPlayers handles that
    });
    
    // Legacy support for old single-button format
    qsa('.btn-player-toggle').forEach(btn => {
        btn.classList.remove('selected', 'team-a', 'team-b');
        btn.disabled = false;
        btn.setAttribute('aria-pressed', 'false');
    });
    
    // Update UI
    updatePlayerButtonStates();
    updateTeamPreview();
    validateForm();
}

function updateTeamColors() {
    // Remove all team classes first from name buttons
    qsa('.player-name-btn').forEach(btn => {
        btn.classList.remove('team-a', 'team-b');
    });
    
    // Apply team colors based on selection order
    // For each court: indices 0-1 (or 4-5) = Team A, indices 2-3 (or 6-7) = Team B
    selectedPlayers.forEach((player, index) => {
        const btn = Array.from(qsa('.player-name-btn')).find(b => b.dataset.player === player);
        if (btn) {
            // Determine team based on position within court
            const positionInCourt = index % 4;
            if (positionInCourt < 2) {
                btn.classList.add('team-a');
            } else {
                btn.classList.add('team-b');
            }
        }
    });
    
    // Legacy support for old single-button format
    qsa('.btn-player-toggle').forEach(btn => {
        btn.classList.remove('team-a', 'team-b');
    });
    
    selectedPlayers.forEach((player, index) => {
        const btn = Array.from(qsa('.btn-player-toggle')).find(b => b.dataset.player === player);
        if (btn) {
            if (index < 2) {
                btn.classList.add('team-a');
            } else {
                btn.classList.add('team-b');
            }
        }
    });
}

async function loadRecommendations() {
    try {
        const response = await api('/api/recommendations');
        
        // Check if dual-court mode
        if (response.dual_court) {
            // Dual-court mode: 8 players across 2 courts
            isDualCourt = true;
            currentCourts = response.matchups || [];
            currentRecommendedIds = response.player_ids || [];
            
            console.log('Dual-court mode enabled:', currentCourts);
            
            // Build legacy currentRecommendation for compatibility
            if (currentCourts.length > 0) {
                currentRecommendation = {
                    teamA: currentCourts[0].team_a,
                    teamB: currentCourts[0].team_b,
                    explanation: currentCourts[0].explanation
                };
            }
        } else {
            // Single-court mode: 4 players
            isDualCourt = false;
            currentRecommendedIds = response.player_ids || [];
            
            // Build currentCourts array with single court for unified handling
            if (response.team_a && response.team_b) {
                currentCourts = [{
                    court: 1,
                    team_a: response.team_a,
                    team_b: response.team_b,
                    explanation: response.explanation
                }];
                
                currentRecommendation = {
                    teamA: response.team_a,
                    teamB: response.team_b,
                    explanation: response.explanation
                };
            }
            
            // Store alternatives for cycling in single-court mode
            allRecommendations = response.recommendations || [];
            recommendationIndex = 0;
        }
        
        // Display the recommendation
        displayRecommendation(recommendationIndex);
        
        // Enable the unified recommendation/cycle button
        // But disable cycling in dual-court mode if there are exactly 8 active players
        // (no other combinations possible)
        const cycleBtn = qs('#btn-cycle-recommendation');
        if (cycleBtn) {
            // In dual-court mode with exactly 8 players, there's only one optimal arrangement
            if (isDualCourt && activePlayersCount === 8) {
                // Keep enabled for initial selection, but cycling won't help
                cycleBtn.disabled = false;
            } else {
                cycleBtn.disabled = false;
            }
        }
    } catch (error) {
        console.log('Failed to load recommendations:', error);
        clearRecommendations();
    }
}

function displayRecommendation(index) {
    // Handle both dual-court and single-court modes
    if (!currentCourts || currentCourts.length === 0) {
        // Fallback to legacy recommendations
        if (!allRecommendations || allRecommendations.length === 0) {
            return;
        }
        const recommendation = allRecommendations[index];
        currentRecommendation = {
            teamA: recommendation.team_a,
            teamB: recommendation.team_b,
            explanation: recommendation.explanation
        };
    }
    
    // Remove existing recommendation classes from name buttons
    qsa('.player-name-btn').forEach(btn => {
        btn.classList.remove('recommend-team-a', 'recommend-team-b', 'court-1', 'court-2');
    });
    
    // Add recommendation highlights based on current mode
    if (isDualCourt && currentCourts.length === 2) {
        // Dual-court: highlight 8 players with court indicators
        const court1 = currentCourts[0];
        const court2 = currentCourts[1];
        
        // Court 1 players
        court1.team_a.forEach(player => {
            const btn = Array.from(qsa('.player-name-btn')).find(b => b.dataset.player === player);
            if (btn) {
                btn.classList.add('recommend-team-a', 'court-1');
            }
        });
        court1.team_b.forEach(player => {
            const btn = Array.from(qsa('.player-name-btn')).find(b => b.dataset.player === player);
            if (btn) {
                btn.classList.add('recommend-team-b', 'court-1');
            }
        });
        
        // Court 2 players
        court2.team_a.forEach(player => {
            const btn = Array.from(qsa('.player-name-btn')).find(b => b.dataset.player === player);
            if (btn) {
                btn.classList.add('recommend-team-a', 'court-2');
            }
        });
        court2.team_b.forEach(player => {
            const btn = Array.from(qsa('.player-name-btn')).find(b => b.dataset.player === player);
            if (btn) {
                btn.classList.add('recommend-team-b', 'court-2');
            }
        });
        
        // Update explanation with both courts
        const explanationEl = qs('#recommendation-explanation');
        if (explanationEl) {
            explanationEl.innerHTML = `Court 1: ${court1.explanation}<br>Court 2: ${court2.explanation}`;
        }
    } else if (currentRecommendation) {
        // Single-court: highlight 4 players
        currentRecommendation.teamA.forEach(player => {
            const btn = Array.from(qsa('.player-name-btn')).find(b => b.dataset.player === player);
            if (btn) {
                btn.classList.add('recommend-team-a');
            }
        });
        
        currentRecommendation.teamB.forEach(player => {
            const btn = Array.from(qsa('.player-name-btn')).find(b => b.dataset.player === player);
            if (btn) {
                btn.classList.add('recommend-team-b');
            }
        });
        
        // Update explanation text
        const explanationEl = qs('#recommendation-explanation');
        if (explanationEl) {
            explanationEl.textContent = currentRecommendation.explanation;
        }
    }
    
    // Legacy support for old single-button format
    qsa('.btn-player-toggle').forEach(btn => {
        btn.classList.remove('recommend-team-a', 'recommend-team-b');
    });
    
    if (currentRecommendation) {
        currentRecommendation.teamA.forEach(player => {
            const btn = Array.from(qsa('.btn-player-toggle')).find(b => b.dataset.player === player);
            if (btn) {
                btn.classList.add('recommend-team-a');
            }
        });
        
        currentRecommendation.teamB.forEach(player => {
            const btn = Array.from(qsa('.btn-player-toggle')).find(b => b.dataset.player === player);
            if (btn) {
                btn.classList.add('recommend-team-b');
            }
        });
    }
}

function clearRecommendations() {
    currentRecommendation = null;
    currentCourts = [];
    currentRecommendedIds = [];
    allRecommendations = [];
    recommendationIndex = 0;
    isDualCourt = false;
    
    // Remove all recommendation highlights and court classes from name buttons
    qsa('.player-name-btn').forEach(btn => {
        btn.classList.remove('recommend-team-a', 'recommend-team-b', 'court-1', 'court-2');
    });
    
    // Legacy support for old single-button format
    qsa('.btn-player-toggle').forEach(btn => {
        btn.classList.remove('recommend-team-a', 'recommend-team-b');
    });
    
    // Clear explanation
    const explanationEl = qs('#recommendation-explanation');
    if (explanationEl) {
        explanationEl.textContent = '';
    }
    
    // Disable unified recommendation/cycle button
    const cycleBtn = qs('#btn-cycle-recommendation');
    if (cycleBtn) {
        cycleBtn.disabled = true;
    }
}

async function cycleRecommendation() {
    console.log('cycleRecommendation called. isDualCourt:', isDualCourt);
    
    if (isDualCourt) {
        // Dual-court mode: fetch new dual-court recommendation (different team arrangement)
        try {
            // Don't exclude players in dual-court mode, just fetch a fresh recommendation
            // The backend will generate a different team arrangement
            console.log('Fetching new dual-court recommendations');
            const response = await api('/api/recommendations');
            console.log('Got response:', response);
            
            // Update state with new recommendations
            if (response.dual_court) {
                currentCourts = response.matchups || [];
                currentRecommendedIds = response.player_ids || [];
                console.log('Updated currentCourts:', currentCourts);
                console.log('Updated currentRecommendedIds:', currentRecommendedIds);
                
                if (currentCourts.length > 0) {
                    currentRecommendation = {
                        teamA: currentCourts[0].team_a,
                        teamB: currentCourts[0].team_b,
                        explanation: currentCourts[0].explanation
                    };
                }
                
                displayRecommendation(0);
            } else {
                // Fallback: backend couldn't provide dual-court (not enough unique players)
                isDualCourt = false;
                if (response.team_a && response.team_b) {
                    currentCourts = [{
                        court: 1,
                        team_a: response.team_a,
                        team_b: response.team_b,
                        explanation: response.explanation
                    }];
                    currentRecommendation = {
                        teamA: response.team_a,
                        teamB: response.team_b,
                        explanation: response.explanation
                    };
                    currentRecommendedIds = response.player_ids || [];
                }
                displayRecommendation(0);
                toast('Not enough unique players for dual-court. Showing single court.', 'info');
            }
        } catch (error) {
            console.error('Failed to cycle recommendations:', error);
            toast('Failed to load new recommendations', 'error');
        }
    } else {
        // Single-court mode: cycle through alternatives
        console.log('Single-court cycling. allRecommendations:', allRecommendations);
        if (!allRecommendations || allRecommendations.length <= 1) {
            console.log('Not enough recommendations to cycle. Length:', allRecommendations?.length);
            return;
        }
        
        // Move to next recommendation (wrap around to beginning)
        recommendationIndex = (recommendationIndex + 1) % allRecommendations.length;
        console.log('New recommendationIndex:', recommendationIndex);
        
        // Update currentRecommendation from the cycled recommendation
        const recommendation = allRecommendations[recommendationIndex];
        currentRecommendation = {
            teamA: recommendation.team_a,
            teamB: recommendation.team_b,
            explanation: recommendation.explanation
        };
        
        // Update currentRecommendedIds for the new recommendation
        currentRecommendedIds = [...recommendation.team_a, ...recommendation.team_b];
        
        displayRecommendation(recommendationIndex);
    }
}

function setRecommendedMatchup() {
    console.log('setRecommendedMatchup called');
    console.log('isDualCourt:', isDualCourt);
    console.log('currentCourts:', currentCourts);
    console.log('currentRecommendation:', currentRecommendation);
    console.log('currentRecommendedIds:', currentRecommendedIds);
    
    // Clear current selections
    selectedPlayers = [];
    
    // Clear from name buttons and remove court classes
    qsa('.player-name-btn').forEach(btn => {
        btn.classList.remove('selected', 'team-a', 'team-b', 'court-1', 'court-2');
        btn.setAttribute('aria-pressed', 'false');
    });
    
    // Legacy support for old single-button format
    qsa('.btn-player-toggle').forEach(btn => {
        btn.classList.remove('selected', 'team-a', 'team-b');
        btn.disabled = false;
        btn.setAttribute('aria-pressed', 'false');
    });
    
    if (isDualCourt && currentCourts.length === 2) {
        // Dual-court mode: select all 8 players based on actual court assignments
        console.log('Selecting 8 players for dual-court');
        
        // Iterate through each court and assign players based on backend matchup
        currentCourts.forEach((court, courtIdx) => {
            const courtNum = court.court;
            const courtClass = `court-${courtNum}`;
            
            // Add Team A players for this court
            court.team_a.forEach(player => {
                const btn = Array.from(qsa('.player-name-btn')).find(b => b.dataset.player === player);
                if (btn && !btn.disabled) {
                    selectedPlayers.push(player);
                    btn.classList.add('selected', 'team-a', courtClass);
                    btn.setAttribute('aria-pressed', 'true');
                }
            });
            
            // Add Team B players for this court
            court.team_b.forEach(player => {
                const btn = Array.from(qsa('.player-name-btn')).find(b => b.dataset.player === player);
                if (btn && !btn.disabled) {
                    selectedPlayers.push(player);
                    btn.classList.add('selected', 'team-b', courtClass);
                    btn.setAttribute('aria-pressed', 'true');
                }
            });
        });
    } else if (currentRecommendation) {
        // Single-court mode: select 4 players directly (don't use togglePlayerSelection)
        console.log('Selecting 4 players for single-court');
        const playersToSelect = [...currentRecommendation.teamA, ...currentRecommendation.teamB];
        console.log('Players to select:', playersToSelect);
        
        playersToSelect.forEach((player, index) => {
            const btn = Array.from(qsa('.player-name-btn')).find(b => b.dataset.player === player);
            if (btn && !btn.disabled) {
                selectedPlayers.push(player);
                btn.classList.add('selected');
                btn.setAttribute('aria-pressed', 'true');
                
                // Add team color (0-1 = team A, 2-3 = team B)
                if (index < 2) {
                    btn.classList.add('team-a');
                } else {
                    btn.classList.add('team-b');
                }
            } else if (!btn) {
                console.error('Button not found for player:', player);
            }
        });
    } else {
        console.error('No recommendation available!');
    }
    
    console.log('Selected players:', selectedPlayers);
    
    // Update UI
    updatePlayerButtonStates();
    applyCourtWatermarksToSelection();
    updateTeamColors();
    updateTeamPreview();
    validateForm();
}

function updateTeamPreview() {
    // Update team names based on selected players and mode
    const court1TeamA = qs('#court1-teamA');
    const court1TeamB = qs('#court1-teamB');
    const court2Row = qs('#court-2-row');
    const court2TeamA = qs('#court2-teamA');
    const court2TeamB = qs('#court2-teamB');
    
    if (!court1TeamA || !court1TeamB) {
        console.error('Court team containers not found');
        return;
    }
    
    // Check if mobile (viewport width <= 768px)
    const isMobile = window.innerWidth <= 768;
    
    // Helper function to format team names
    const formatTeamNames = (players) => {
        if (isMobile) {
            // Mobile: stack names vertically using div elements
            return players.map(name => `<div>${escapeHtml(name)}</div>`).join('');
        } else {
            // Desktop: join with &
            return escapeHtml(players.join(' & '));
        }
    };
    
    // Court 1 (first 4 players)
    if (selectedPlayers.length >= 2) {
        court1TeamA.innerHTML = formatTeamNames(selectedPlayers.slice(0, 2));
    } else {
        court1TeamA.innerHTML = '';
    }
    
    if (selectedPlayers.length >= 4) {
        court1TeamB.innerHTML = formatTeamNames(selectedPlayers.slice(2, 4));
    } else {
        court1TeamB.innerHTML = '';
    }
    
    // Court 2 (players 4-7) - show/hide based on dual-court mode
    if (activePlayersCount >= 8 && selectedPlayers.length >= 8) {
        // Show court 2
        if (court2Row) {
            court2Row.hidden = false;
        }
        
        // Show court numbers when 8+ players
        const court1Number = qs('#court-1-number');
        const court2Number = qs('#court-2-number');
        if (court1Number) court1Number.hidden = false;
        if (court2Number) court2Number.hidden = false;
        
        if (court2TeamA && court2TeamB) {
            if (selectedPlayers.length >= 6) {
                court2TeamA.innerHTML = formatTeamNames(selectedPlayers.slice(4, 6));
            } else {
                court2TeamA.innerHTML = '';
            }
            
            if (selectedPlayers.length >= 8) {
                court2TeamB.innerHTML = formatTeamNames(selectedPlayers.slice(6, 8));
            } else {
                court2TeamB.innerHTML = '';
            }
        }
    } else {
        // Hide court 2
        if (court2Row) {
            court2Row.hidden = true;
        }
        
        // Hide court numbers when less than 8 players
        const court1Number = qs('#court-1-number');
        const court2Number = qs('#court-2-number');
        if (court1Number) court1Number.hidden = true;
        if (court2Number) court2Number.hidden = true;
    }
}

function validateForm() {
    const court1ScoreA = qs('#court1-score-a');
    const court1ScoreB = qs('#court1-score-b');
    const court2ScoreA = qs('#court2-score-a');
    const court2ScoreB = qs('#court2-score-b');
    
    let isValid = false;
    
    if (activePlayersCount >= 8) {
        // Dual-court mode: require 8 players and 4 score inputs
        const hasCourt1Scores = court1ScoreA && court1ScoreB && 
            court1ScoreA.value !== '' && court1ScoreB.value !== '' &&
            parseInt(court1ScoreA.value) >= 0 && parseInt(court1ScoreB.value) >= 0;
        
        const hasCourt2Scores = court2ScoreA && court2ScoreB &&
            court2ScoreA.value !== '' && court2ScoreB.value !== '' &&
            parseInt(court2ScoreA.value) >= 0 && parseInt(court2ScoreB.value) >= 0;
        
        isValid = 
            selectedPlayers.length === 8 &&
            selectedBet !== null &&
            hasCourt1Scores &&
            hasCourt2Scores;
    } else {
        // Single-court mode: require 4 players and 2 score inputs
        const hasScores = court1ScoreA && court1ScoreB &&
            court1ScoreA.value !== '' && court1ScoreB.value !== '' &&
            parseInt(court1ScoreA.value) >= 0 && parseInt(court1ScoreB.value) >= 0;
        
        isValid = 
            selectedPlayers.length === 4 &&
            selectedBet !== null &&
            hasScores;
    }
    
    const recordBtn = qs('#recordMatchBtn');
    if (recordBtn) {
        recordBtn.disabled = !isValid;
    }
    
    // Update debug display
    const debugPlayers = qs('#debugPlayers');
    const debugBet = qs('#debugBet');
    const debugScores = qs('#debugScores');
    const debugButton = qs('#debugButton');
    
    if (debugPlayers) debugPlayers.textContent = `Players: ${selectedPlayers.length}/4`;
    if (debugBet) debugBet.textContent = `Bet: ${selectedBet !== null ? '$' + selectedBet : 'Not selected'}`;
    if (debugScores) debugScores.textContent = `Scores: ${hasScores ? 'Yes' : 'No'}`;
    if (debugButton) debugButton.textContent = `Button: ${isValid ? 'Enabled' : 'Disabled'}`;
}

async function handleRecordMatch() {
    console.log('handleRecordMatch called');
    console.log('Selected players:', selectedPlayers);
    console.log('Selected bet:', selectedBet);
    console.log('Active players count:', activePlayersCount);
    
    try {
        if (activePlayersCount >= 8 && selectedPlayers.length === 8) {
            // Dual-court mode: Submit 2 matches
            const court1ScoreA = parseInt(qs('#court1-score-a').value);
            const court1ScoreB = parseInt(qs('#court1-score-b').value);
            const court2ScoreA = parseInt(qs('#court2-score-a').value);
            const court2ScoreB = parseInt(qs('#court2-score-b').value);
            
            const court1Payload = {
                team1: selectedPlayers.slice(0, 2),
                team2: selectedPlayers.slice(2, 4),
                team1_score: court1ScoreA,
                team2_score: court1ScoreB,
                game_value: selectedBet
            };
            
            const court2Payload = {
                team1: selectedPlayers.slice(4, 6),
                team2: selectedPlayers.slice(6, 8),
                team1_score: court2ScoreA,
                team2_score: court2ScoreB,
                game_value: selectedBet
            };
            
            console.log('Court 1 Payload:', court1Payload);
            console.log('Court 2 Payload:', court2Payload);
            
            // Submit Court 1 match
            console.log('Submitting Court 1 match...');
            const result1 = await api('/api/matches', {
                method: 'POST',
                body: JSON.stringify(court1Payload)
            });
            console.log('Court 1 match recorded:', result1);
            
            // Submit Court 2 match
            console.log('Submitting Court 2 match...');
            try {
                const result2 = await api('/api/matches', {
                    method: 'POST',
                    body: JSON.stringify(court2Payload)
                });
                console.log('Court 2 match recorded:', result2);
                toast('Both matches recorded successfully!');
            } catch (court2Error) {
                console.error('Error recording Court 2 match:', court2Error);
                toast('Court 1 recorded, but Court 2 failed. Please record Court 2 manually.', 'error');
                // Don't reset form so user can retry Court 2
                await loadMatchHistory();
                await loadSessionStats();
                await loadPlayerEarnings();
                return;
            }
        } else {
            // Single-court mode: Submit 1 match
            const court1ScoreA = parseInt(qs('#court1-score-a').value);
            const court1ScoreB = parseInt(qs('#court1-score-b').value);
            
            const payload = {
                team1: selectedPlayers.slice(0, 2),
                team2: selectedPlayers.slice(2, 4),
                team1_score: court1ScoreA,
                team2_score: court1ScoreB,
                game_value: selectedBet
            };
            
            console.log('Payload:', payload);
            console.log('Calling API...');
            
            const result = await api('/api/matches', {
                method: 'POST',
                body: JSON.stringify(payload)
            });
            
            console.log('Match recorded:', result);
            toast('Match recorded successfully');
        }
        
        // Reset form
        console.log('Resetting form...');
        resetMatchForm();
        
        // Reload data
        console.log('Reloading data...');
        await loadMatchHistory();
        await loadSessionStats();
        await loadPlayerEarnings();
        await loadRecommendations();
        console.log('All done!');
    } catch (error) {
        console.error('Error recording match:', error);
        console.error('Error details:', error.stack);
        toast(error.message || 'Failed to record match', 'error');
    }
}

function resetMatchForm() {
    // Clear player selection
    selectedPlayers = [];
    
    // Clear from name buttons and remove court classes
    qsa('.player-name-btn').forEach(btn => {
        btn.classList.remove('selected', 'team-a', 'team-b', 'court-1', 'court-2');
        btn.setAttribute('aria-pressed', 'false');
        // Don't modify disabled state - renderPlayers handles that based on active status
    });
    
    // Legacy support for old single-button format
    qsa('.btn-player-toggle').forEach(btn => {
        btn.classList.remove('selected', 'team-a', 'team-b');
        btn.disabled = false;
        btn.setAttribute('aria-pressed', 'false');
    });
    
    // Restore last bet selection (don't clear it)
    if (lastSelectedBet !== null) {
        selectedBet = lastSelectedBet;
        qsa('.btn-bet').forEach(btn => {
            if (parseInt(btn.dataset.value) === lastSelectedBet) {
                btn.classList.add('selected');
                btn.setAttribute('aria-pressed', 'true');
            } else {
                btn.classList.remove('selected');
                btn.setAttribute('aria-pressed', 'false');
            }
        });
    } else {
        selectedBet = null;
        qsa('.btn-bet').forEach(btn => {
            btn.classList.remove('selected');
            btn.setAttribute('aria-pressed', 'false');
        });
    }
    
    // Clear scores from all courts
    const court1ScoreA = qs('#court1-score-a');
    const court1ScoreB = qs('#court1-score-b');
    const court2ScoreA = qs('#court2-score-a');
    const court2ScoreB = qs('#court2-score-b');
    
    if (court1ScoreA) court1ScoreA.value = '';
    if (court1ScoreB) court1ScoreB.value = '';
    if (court2ScoreA) court2ScoreA.value = '';
    if (court2ScoreB) court2ScoreB.value = '';
    
    // Clear team preview text
    const court1TeamA = qs('#court1-teamA');
    const court1TeamB = qs('#court1-teamB');
    const court2TeamA = qs('#court2-teamA');
    const court2TeamB = qs('#court2-teamB');
    
    if (court1TeamA) court1TeamA.textContent = '';
    if (court1TeamB) court1TeamB.textContent = '';
    if (court2TeamA) court2TeamA.textContent = '';
    if (court2TeamB) court2TeamB.textContent = '';
    
    // Hide court 2 and court numbers
    const court2Row = qs('#court-2-row');
    const court1Number = qs('#court-1-number');
    const court2Number = qs('#court-2-number');
    
    if (court2Row) court2Row.hidden = true;
    if (court1Number) court1Number.hidden = true;
    if (court2Number) court2Number.hidden = true;
    
    // Update button states
    updatePlayerButtonStates();
    
    // Disable submit
    const recordBtn = qs('#recordMatchBtn');
    if (recordBtn) recordBtn.disabled = true;
}

function updateSessionDisplay() {
    if (!currentSession) return;
    
    // Update session date
    const sessionDate = qs('#sessionDate');
    if (sessionDate) {
        sessionDate.textContent = formatDate(currentSession.date);
    }
    
    // Update game count
    const countSpan = qs('#todayGamesCount');
    if (countSpan) {
        countSpan.textContent = currentSession.match_count;
    }
}

async function loadMatchHistory() {
    try {
        // Refresh current session data
        currentSession = await api('/api/sessions/current');
        
        // Get matches for current session
        const sessionData = await api(`/api/sessions/${currentSession.session_id}`);
        const matches = sessionData.matches || [];
        const tbody = qs('#matchHistoryBody');
        
        // Update session display
        updateSessionDisplay();
        
        if (matches.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="table-empty">No matches in today\'s session yet</td></tr>';
            return;
        }
        
        // Sort by game number descending (newest first)
        matches.sort((a, b) => b.game_number - a.game_number);
        
        // Compute session-specific game numbers
        const total = matches.length;
        matches.forEach((m, i) => {
            // index 0 (newest) gets total, last (oldest) gets 1
            m.sessionGameNumber = total - i;
        });
        
        // Detect mobile viewport
        const isMobile = window.matchMedia('(max-width: 768px)').matches;
        
        // Helper function to render team names
        const renderTeam = (teamArray) => {
            const escapedNames = teamArray.map(name => escapeHtml(name));
            if (isMobile) {
                // Stack names vertically on mobile
                return escapedNames.join('<br>');
            } else {
                // Keep names inline on desktop
                return escapedNames.join(' & ');
            }
        };
        
        tbody.innerHTML = matches.map(match => {
            const team1Won = match.team1_score > match.team2_score;
            const team1Class = team1Won ? 'team-cell team-a match-winner match-team-a' : 'team-cell team-a match-team-a';
            const team2Class = !team1Won ? 'team-cell team-b match-winner match-team-b' : 'team-cell team-b match-team-b';
            const scoreDisplay = `${match.team1_score}-${match.team2_score}`;
            
            return `
                <tr>
                    <td class="col-number">${match.sessionGameNumber}</td>
                    <td class="${team1Class}">${renderTeam(match.team1)}</td>
                    <td class="col-score" style="text-align: center;">${scoreDisplay}</td>
                    <td class="${team2Class}">${renderTeam(match.team2)}</td>
                    <td class="col-bet" style="text-align: right;">${formatCurrency(match.game_value)}</td>
                    <td class="col-action" style="text-align: center;">
                        <button class="btn btn-danger btn-small" onclick="deleteMatchFromHistory('${match.match_id}')" title="Delete match">
                            ×
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        toast('Failed to load match history', 'error');
    }
}

async function deleteMatchFromHistory(matchId) {
    if (!confirm('Are you sure you want to delete this match?')) {
        return;
    }
    
    try {
        await api(`/api/matches/${matchId}`, {
            method: 'DELETE'
        });
        
        toast('Match deleted successfully');
        await loadMatchHistory();
        await loadSessionStats();
    } catch (error) {
        toast(error.message, 'error');
    }
}

async function loadSessionStats() {
    try {
        if (!currentSession || !currentSession.session_id) {
            console.error('loadSessionStats: No current session');
            return;
        }
        
        const statsData = await api(`/api/sessions/${currentSession.session_id}/stats`);
        
        // Render player stats with bar chart
        const playerTbody = qs('#playerStatsBody');
        if (playerTbody) {
            if (!statsData.players || statsData.players.length === 0) {
                playerTbody.innerHTML = '<tr><td colspan="3" class="table-empty">No games in this session yet</td></tr>';
            } else {
                playerTbody.innerHTML = statsData.players.map(player => {
                    const winPercent = player.winRate;
                    const lossPercent = 100 - winPercent;
                    
                    return `
                        <tr>
                            <td>${escapeHtml(player.name)}</td>
                            <td style="text-align: center;">${player.games}</td>
                            <td>
                                <div class="win-rate-bar">
                                    <div class="win-rate-bar-segment win-segment" style="width: ${winPercent}%;"></div>
                                    <div class="win-rate-bar-segment loss-segment" style="width: ${lossPercent}%;"></div>
                                    <div class="win-rate-label">${winPercent}%</div>
                                </div>
                            </td>
                        </tr>
                    `;
                }).join('');
            }
        }
        
        // Render partnership stats
        const partnershipTbody = qs('#partnershipStatsBody');
        if (partnershipTbody) {
            if (!statsData.partnerships || statsData.partnerships.length === 0) {
                partnershipTbody.innerHTML = '<tr><td colspan="5" class="table-empty">No partnerships recorded yet</td></tr>';
            } else {
                partnershipTbody.innerHTML = statsData.partnerships.map(partnership => `
                    <tr>
                        <td>${escapeHtml(partnership.partnership)}</td>
                        <td style="text-align: right;">${partnership.games}</td>
                        <td style="text-align: right;">${partnership.wins}</td>
                        <td style="text-align: right;">${partnership.losses}</td>
                        <td style="text-align: right;">${partnership.winRate}%</td>
                    </tr>
                `).join('');
            }
        }
    } catch (error) {
        console.error('Failed to load session stats:', error);
        toast('Failed to load session stats', 'error');
    }
}

async function loadPlayerEarnings() {
    try {
        console.log('loadPlayerEarnings: Starting...');
        
        if (!currentSession || !currentSession.session_id) {
            console.error('loadPlayerEarnings: No current session');
            return;
        }
        
        // Get session-specific earnings
        const earningsData = await api(`/api/sessions/${currentSession.session_id}/earnings`);
        const earnings = earningsData.players || [];
        console.log('loadPlayerEarnings: Earnings data:', earnings);
        
        const container = qs('#playerEarningsList');
        console.log('loadPlayerEarnings: Found container:', container);
        
        if (!container) {
            console.error('loadPlayerEarnings: playerEarningsList element not found!');
            return;
        }
        
        if (earnings.length === 0) {
            console.log('loadPlayerEarnings: No earnings data, showing empty message');
            container.innerHTML = '<div style="color: var(--text-muted); font-size: 0.875rem;">No earnings data yet</div>';
            return;
        }
        
        console.log(`loadPlayerEarnings: Rendering ${earnings.length} players`);
        
        // Build compact earnings display with expandable rows
        const earningsHtml = earnings.map(player => {
            const earningsFormatted = formatEarnings(player.net_earnings);
            const slug = slugifyName(player.player);
            return `
                <div class="earnings-item earnings-item-clickable" 
                     id="earnings-row-${slug}"
                     data-player="${escapeHtml(player.player)}"
                     role="button"
                     tabindex="0"
                     aria-expanded="false"
                     onclick="toggleEarningsPlayer('${escapeHtml(player.player).replace(/'/g, "\\'")}')"
                     onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();toggleEarningsPlayer('${escapeHtml(player.player).replace(/'/g, "\\'")}');}">
                    <span class="earnings-player">${escapeHtml(player.player)}</span>
                    <span>
                        <span class="earnings-amount ${earningsFormatted.className}">${earningsFormatted.text}</span>
                        <span class="earnings-games">(${player.games_played})</span>
                    </span>
                </div>
                <div class="earnings-details is-collapsed" id="earnings-details-${slug}">
                    <!-- Details loaded on demand -->
                </div>
            `;
        }).join('');
        
        container.innerHTML = earningsHtml;
        console.log('loadPlayerEarnings: Rendering complete');
    } catch (error) {
        console.error('loadPlayerEarnings ERROR:', error);
        toast('Failed to load player earnings', 'error');
    }
}

// ==================== History Page ====================

let sessionsCache = {};
let expandedSessions = new Set();

// Earnings expansion state
let expandedEarningsPlayer = null;
let expandedEarningsEls = { row: null, details: null };

// Utility: slugify player name for safe element IDs
function slugifyName(name) {
    return name.replace(/[^a-zA-Z0-9]/g, '-').toLowerCase();
}

// Collapse currently expanded earnings player
function collapseCurrentEarningsExpansion() {
    if (expandedEarningsPlayer && expandedEarningsEls.row && expandedEarningsEls.details) {
        expandedEarningsEls.row.classList.remove('expanded');
        expandedEarningsEls.row.setAttribute('aria-expanded', 'false');
        expandedEarningsEls.details.classList.remove('is-expanded');
        expandedEarningsEls.details.classList.add('is-collapsed');
        expandedEarningsPlayer = null;
        expandedEarningsEls = { row: null, details: null };
    }
}

// Toggle earnings player expansion
function toggleEarningsPlayer(playerName) {
    const slug = slugifyName(playerName);
    const row = qs(`#earnings-row-${slug}`);
    const detailsEl = qs(`#earnings-details-${slug}`);
    
    if (!row || !detailsEl) return;
    
    // If this player is already expanded, collapse it
    if (expandedEarningsPlayer === playerName) {
        collapseCurrentEarningsExpansion();
        return;
    }
    
    // Collapse any other expanded player
    if (expandedEarningsPlayer && expandedEarningsPlayer !== playerName) {
        collapseCurrentEarningsExpansion();
    }
    
    // Expand this player
    row.classList.add('expanded');
    row.setAttribute('aria-expanded', 'true');
    detailsEl.classList.remove('is-collapsed');
    detailsEl.classList.add('is-expanded');
    
    // Update state
    expandedEarningsPlayer = playerName;
    expandedEarningsEls = { row, details: detailsEl };
    
    // Load details if not already loaded
    if (!detailsEl.hasAttribute('data-loaded')) {
        loadPlayerMatchDetails(playerName, detailsEl);
    }
}

// Load and display match details for a player
async function loadPlayerMatchDetails(playerName, targetEl) {
    // Show loading state
    targetEl.innerHTML = '<div style="color: var(--text-muted); font-size: 0.875rem; padding: 0.5rem 0;">Loading match details...</div>';
    
    try {
        const data = await api(`/api/current-session/player/${encodeURIComponent(playerName)}/matches`);
        
        if (!data.matches || data.matches.length === 0) {
            targetEl.innerHTML = '<div style="color: var(--text-muted); font-size: 0.875rem; padding: 0.5rem 0;">No matches for this session</div>';
            targetEl.setAttribute('data-loaded', 'true');
            return;
        }
        
        // Render match bet lines
        const matchesHtml = data.matches.map(match => {
            const amountClass = match.amount_delta > 0 ? 'amount-positive' : (match.amount_delta < 0 ? 'amount-negative' : '');
            const amountSign = match.amount_delta > 0 ? '+' : '';
            
            return `
                <div class="match-bet-line">
                    <span class="match-bet-game">Game ${match.game_number}</span>
                    <span class="match-bet-amount ${amountClass}">${amountSign}$${Math.abs(match.amount_delta).toFixed(2)}</span>
                </div>
            `;
        }).join('');
        
        targetEl.innerHTML = matchesHtml;
        targetEl.setAttribute('data-loaded', 'true');
    } catch (error) {
        console.error('Failed to load player match details:', error);
        targetEl.innerHTML = `
            <div style="color: var(--text-danger); font-size: 0.875rem; padding: 0.5rem 0;">
                Failed to load match details. 
                <button class="btn btn-secondary btn-small" onclick="loadPlayerMatchDetails('${escapeHtml(playerName).replace(/'/g, "\\'") }', document.querySelector('#earnings-details-${slugifyName(playerName)}'))">Retry</button>
            </div>
        `;
    }
}

async function initHistory() {
    await loadSessions();
}

async function loadSessions() {
    try {
        const sessions = await api('/api/sessions');
        const tbody = qs('#sessionsTableBody');
        
        if (sessions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="table-empty">No sessions recorded yet</td></tr>';
            return;
        }
        
        // Build session rows - will populate pills/text after fetching match data
        const rowsHtml = await Promise.all(sessions.map(async session => {
            // Detect mobile viewport
            const isMobile = window.matchMedia('(max-width: 768px)').matches;
            let playersHtml = '<div>Loading...</div>';
            
            let players = [];
            let playerAverage = 0;
            
            try {
                // Fetch earnings data for this session
                const earningsData = await api(`/api/sessions/${session.session_id}/earnings`);
                players = earningsData.players || [];
                
                // Calculate player average: sum of games each player played / number of players
                const totalGamesPlayed = players.reduce((sum, p) => sum + (p.games_played || 0), 0);
                playerAverage = players.length > 0 ? Math.round(totalGamesPlayed / players.length) : 0;
                
                if (isMobile) {
                    // Mobile: Just show player count
                    playersHtml = players.length > 0 ? `${players.length}` : 'No players';
                } else {
                    // Desktop: Show pills with earnings, sorted by earnings descending
                    players.sort((a, b) => b.net_earnings - a.net_earnings);
                    
                    // Build pills HTML with earnings
                    const pillsHtml = players.map(p => {
                        const earningsStr = formatSignedInt(p.net_earnings);
                        // Determine pill color based on earnings
                        let pillClass = 'player-pill--neutral';
                        if (p.net_earnings > 0) {
                            pillClass = 'player-pill--green';
                        } else if (p.net_earnings < 0) {
                            pillClass = 'player-pill--red';
                        }
                        // else stays neutral (grey) for 0 earnings
                        
                        return `<span class="player-pill ${pillClass}">${escapeHtml(p.player)} ${earningsStr}</span>`;
                    }).join('');
                    
                    playersHtml = `<div class="player-pills-container">
                        ${pillsHtml || '<span style="color: var(--text-muted);">No players</span>'}
                    </div>`;
                }
            } catch (err) {
                console.error(`Failed to load players for session ${session.session_id}:`, err);
                playersHtml = session.players.join(', ') || 'No players';
            }
            
            // Format games column: combine avg and total with bullet
            const gamesDisplay = `${playerAverage} \u2022 ${session.match_count}`;
            
            return `
                <tr data-session-id="${session.session_id}" data-session-date="${session.date}" class="session-row" onclick="toggleSession('${session.session_id}')" style="cursor: pointer;">
                    <td onclick="event.stopPropagation();">
                        <div class="session-date-cell">
                            <button class="btn-icon-small" 
                                    onclick="event.stopPropagation(); startSessionDateEdit('${session.session_id}')" 
                                    aria-label="Edit session date"
                                    title="Edit date">
                                ✎
                            </button>
                            <div class="session-date-display">
                                ${formatDateDesign(session.date)}
                            </div>
                        </div>
                    </td>
                    <td>${playersHtml}</td>
                    <td style="text-align: center;">${gamesDisplay}</td>
                    <td style="text-align: center;" onclick="event.stopPropagation();">
                        <button class="btn btn-danger btn-small" onclick="deleteSession('${session.session_id}', ${session.match_count})" aria-label="Delete session" style="padding: 0.35rem 0.65rem; font-size: 1.25rem; line-height: 1;">
                            &times;
                        </button>
                    </td>
                </tr>
                <tr id="expand-${session.session_id}" class="session-details" style="display: none;">
                    <td colspan="4">
                        <div style="margin: 0.5rem;">
                            <!-- Tabbed Carousel -->
                            <div class="card" style="margin: 0;">
                                <div class="card-header">
                                    <nav class="card-header-tabs" role="tablist" aria-label="Session data tabs">
                                        <button type="button" 
                                                class="tab-item active" 
                                                data-session-id="${session.session_id}"
                                                data-tab-target="history" 
                                                role="tab" 
                                                aria-selected="true"
                                                onclick="switchHistoryTab('${session.session_id}', 'history')">
                                            History
                                        </button>
                                        <button type="button" 
                                                class="tab-item" 
                                                data-session-id="${session.session_id}"
                                                data-tab-target="earnings" 
                                                role="tab" 
                                                aria-selected="false"
                                                onclick="switchHistoryTab('${session.session_id}', 'earnings')">
                                            Earnings
                                        </button>
                                        <button type="button" 
                                                class="tab-item" 
                                                data-session-id="${session.session_id}"
                                                data-tab-target="stats" 
                                                role="tab" 
                                                aria-selected="false"
                                                onclick="switchHistoryTab('${session.session_id}', 'stats')">
                                            Stats
                                        </button>
                                    </nav>
                                </div>
                                <div class="carousel-card-body">
                                    <!-- Pane 1: Match History (default visible) -->
                                    <section id="pane-history-${session.session_id}" class="carousel-pane is-active" role="tabpanel">
                                        <div class="table-scroll">
                                            <table class="table table-compact">
                                                <thead>
                                                    <tr>
                                                        <th style="width: 60px;">#</th>
                                                        <th><span style="color: var(--team-a);">A</span></th>
                                                        <th style="width: 80px; text-align: center;">Score</th>
                                                        <th><span style="color: var(--team-b);">B</span></th>
                                                        <th style="width: 80px; text-align: center;">Bet</th>
                                                    </tr>
                                                </thead>
                                                <tbody id="matches-${session.session_id}">
                                                    <tr><td colspan="5" class="table-empty">Loading...</td></tr>
                                                </tbody>
                                            </table>
                                        </div>
                                    </section>
                                    
                                    <!-- Pane 2: Session Earnings (hidden by default) -->
                                    <section id="pane-earnings-${session.session_id}" class="carousel-pane" role="tabpanel" hidden>
                                        <div class="session-earnings-mini" id="earnings-${session.session_id}">
                                            <div style="color: var(--text-muted); font-size: 0.875rem;">Loading...</div>
                                        </div>
                                    </section>
                                    
                                    <!-- Pane 3: Player Stats (hidden by default) -->
                                    <section id="pane-stats-${session.session_id}" class="carousel-pane" role="tabpanel" hidden>
                                        <div style="padding: 1rem; overflow-y: auto;">
                                            <div class="table-container">
                                                <table class="stats-table compact stats-table-barchart">
                                                    <thead>
                                                        <tr>
                                                            <th>Name</th>
                                                            <th style="text-align: center; width: 40px;">G</th>
                                                            <th style="min-width: 150px;">Win Rate</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody id="stats-${session.session_id}">
                                                        <tr>
                                                            <td colspan="3" class="table-empty">Loading...</td>
                                                        </tr>
                                                    </tbody>
                                                </table>
                                            </div>
                                        </div>
                                    </section>
                                </div>
                            </div>
                        </div>
                    </td>
                </tr>
            `;
        }));
        
        tbody.innerHTML = rowsHtml.join('');
        
        sessionsCache = {};
        sessions.forEach(s => {
            sessionsCache[s.session_id] = s;
        });
    } catch (error) {
        toast('Failed to load sessions', 'error');
    }
}

async function toggleSession(sessionId) {
    const expandRow = qs(`#expand-${sessionId}`);
    const sessionRow = qs(`tr[data-session-id="${sessionId}"]`);
    
    // Don't toggle if currently editing
    if (sessionRow && sessionRow.dataset.editing === 'true') {
        return;
    }
    
    if (expandedSessions.has(sessionId)) {
        // Collapse
        expandRow.style.display = 'none';
        expandedSessions.delete(sessionId);
    } else {
        // Expand
        expandRow.style.display = 'table-row';
        expandedSessions.add(sessionId);
        
        // Load matches if not already loaded
        await loadSessionMatches(sessionId);
    }
}

function startSessionDateEdit(sessionId) {
    const sessionRow = qs(`tr[data-session-id="${sessionId}"]`);
    if (!sessionRow) return;
    
    const dateCell = sessionRow.querySelector('.session-date-cell');
    if (!dateCell) return;
    
    // Mark row as editing to prevent expansion
    sessionRow.dataset.editing = 'true';
    
    // Get current date from data attribute
    const currentDate = sessionRow.dataset.sessionDate;
    
    // Store original HTML
    if (!dateCell.dataset.originalHtml) {
        dateCell.dataset.originalHtml = dateCell.innerHTML;
    }
    
    // Replace with edit UI
    dateCell.classList.add('is-editing');
    dateCell.innerHTML = `
        <div class="session-date-edit">
            <input type="date" 
                   class="session-date-input" 
                   id="date-input-${sessionId}" 
                   value="${currentDate}"
                   aria-label="Edit session date">
            <div class="session-date-actions">
                <button class="btn-save" 
                        onclick="saveSessionDateEdit('${sessionId}')"
                        aria-label="Save date">
                    Save
                </button>
                <button class="btn-cancel" 
                        onclick="cancelSessionDateEdit('${sessionId}')"
                        aria-label="Cancel edit">
                    Cancel
                </button>
            </div>
        </div>
    `;
    
    // Focus the input
    const input = qs(`#date-input-${sessionId}`);
    if (input) {
        input.focus();
        
        // Add keyboard support
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                saveSessionDateEdit(sessionId);
            } else if (e.key === 'Escape') {
                e.preventDefault();
                cancelSessionDateEdit(sessionId);
            }
        });
    }
}

function cancelSessionDateEdit(sessionId) {
    const sessionRow = qs(`tr[data-session-id="${sessionId}"]`);
    if (!sessionRow) return;
    
    const dateCell = sessionRow.querySelector('.session-date-cell');
    if (!dateCell || !dateCell.dataset.originalHtml) return;
    
    // Restore original HTML
    dateCell.classList.remove('is-editing');
    dateCell.innerHTML = dateCell.dataset.originalHtml;
    delete dateCell.dataset.originalHtml;
    
    // Clear editing flag
    delete sessionRow.dataset.editing;
}

async function saveSessionDateEdit(sessionId) {
    const sessionRow = qs(`tr[data-session-id="${sessionId}"]`);
    if (!sessionRow) return;
    
    const input = qs(`#date-input-${sessionId}`);
    if (!input) return;
    
    const newDate = input.value;
    const currentDate = sessionRow.dataset.sessionDate;
    
    // Validate date
    if (!newDate || !/^\d{4}-\d{2}-\d{2}$/.test(newDate)) {
        toast('Invalid date. Please use YYYY-MM-DD format', 'error');
        return;
    }
    
    // Check if date changed
    if (newDate === currentDate) {
        cancelSessionDateEdit(sessionId);
        return;
    }
    
    // Validate year range (prevent obvious typos)
    const year = parseInt(newDate.split('-')[0]);
    if (year < 2000 || year > 2100) {
        toast('Please enter a valid year', 'error');
        return;
    }
    
    // Show loading state
    const dateCell = sessionRow.querySelector('.session-date-cell');
    const saveBtn = dateCell.querySelector('.btn-save');
    const cancelBtn = dateCell.querySelector('.btn-cancel');
    
    if (input) input.disabled = true;
    if (saveBtn) saveBtn.disabled = true;
    if (cancelBtn) cancelBtn.disabled = true;
    
    // Add loading indicator
    const loadingSpan = document.createElement('span');
    loadingSpan.className = 'session-date-loading';
    loadingSpan.textContent = 'Saving...';
    dateCell.querySelector('.session-date-edit').appendChild(loadingSpan);
    
    try {
        const result = await patchSessionDate(sessionId, newDate, false);
        
        // Success
        if (result.merged) {
            toast('Session date updated and merged with existing session');
        } else {
            toast('Session date updated');
        }
        
        // Reload sessions list
        expandedSessions.clear();
        await loadSessions();
        
    } catch (error) {
        // Remove loading state
        if (loadingSpan) loadingSpan.remove();
        if (input) input.disabled = false;
        if (saveBtn) saveBtn.disabled = false;
        if (cancelBtn) cancelBtn.disabled = false;
        
        // Handle different error types
        if (error.status === 409) {
            // Conflict - ask user if they want to merge
            const shouldMerge = confirm(
                `A session already exists for ${newDate}. ` +
                `Do you want to merge this session with the existing one? ` +
                `All matches will be moved to the existing session.`
            );
            
            if (shouldMerge) {
                // Retry with merge=true
                try {
                    const mergeResult = await patchSessionDate(sessionId, newDate, true);
                    toast('Session date updated and merged with existing session');
                    
                    // Reload sessions list
                    expandedSessions.clear();
                    await loadSessions();
                } catch (mergeError) {
                    toast(mergeError.message || 'Could not merge sessions', 'error');
                }
            }
        } else if (error.status === 404) {
            toast('Session not found. Reloading...', 'error');
            await loadSessions();
        } else if (error.status === 400) {
            toast(error.message || 'Invalid date', 'error');
        } else {
            toast(error.message || 'Could not update session date', 'error');
        }
    }
}

async function patchSessionDate(sessionId, newDate, merge = false) {
    const response = await fetch(`/api/sessions/${sessionId}`, {
        method: 'PATCH',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            date: newDate,
            merge: merge
        })
    });
    
    const data = await response.json();
    
    if (!response.ok) {
        const error = new Error(data.error || 'Request failed');
        error.status = response.status;
        error.data = data;
        throw error;
    }
    
    return data;
}

async function loadSessionMatches(sessionId) {
    try {
        const sessionData = await api(`/api/sessions/${sessionId}`);
        const tbody = qs(`#matches-${sessionId}`);
        
        if (sessionData.matches.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="table-empty">No matches in this session</td></tr>';
        } else {
            // Sort by game number
            sessionData.matches.sort((a, b) => a.game_number - b.game_number);
            
            // Detect mobile viewport
            const isMobile = window.matchMedia('(max-width: 768px)').matches;
            
            tbody.innerHTML = sessionData.matches.map((match, index) => {
                // Use session-specific game number (1-based index)
                const sessionGameNumber = index + 1;
                
                // Determine winner and apply team color classes
                const team1Won = match.team1_score > match.team2_score;
                const team1Class = team1Won ? 'match-team-a match-winner' : 'match-team-a';
                const team2Class = !team1Won ? 'match-team-b match-winner' : 'match-team-b';
                
                // Format team names - compact on mobile
                const team1Display = isMobile ? match.team1.map(n => escapeHtml(n)).join('<br>') : match.team1.join(' & ');
                const team2Display = isMobile ? match.team2.map(n => escapeHtml(n)).join('<br>') : match.team2.join(' & ');
                
                // Format score - combined on mobile, separate desktop shows combined too
                const scoreDisplay = `${match.team1_score}-${match.team2_score}`;
                
                return `
                    <tr>
                        <td>${sessionGameNumber}</td>
                        <td class="${team1Class}">${team1Display}</td>
                        <td style="text-align: center;">${scoreDisplay}</td>
                        <td class="${team2Class}">${team2Display}</td>
                        <td style="text-align: center;">${formatCurrency(match.game_value)}</td>
                    </tr>
                `;
            }).join('');
        }
        
        // Load session earnings and stats
        await loadSessionEarnings(sessionId);
        await loadHistorySessionStats(sessionId);
    } catch (error) {
        toast('Failed to load session matches', 'error');
    }
}

async function loadSessionEarnings(sessionId) {
    try {
        const earningsData = await api(`/api/sessions/${sessionId}/earnings`);
        const container = qs(`#earnings-${sessionId}`);
        
        if (!container) return;
        
        const players = earningsData.players || [];
        
        if (players.length === 0) {
            container.innerHTML = '<h4>Session Earnings</h4><div style="color: var(--text-muted); font-size: 0.875rem;">No earnings data</div>';
            return;
        }
        
        // Build compact earnings display
        const earningsHtml = players.map(player => {
            const earnings = formatEarnings(player.net_earnings);
            return `
                <div class="earnings-item">
                    <span class="earnings-player">${escapeHtml(player.player)}</span>
                    <span>
                        <span class="earnings-amount ${earnings.className}">${earnings.text}</span>
                        <span class="earnings-games">(${player.games_played})</span>
                    </span>
                </div>
            `;
        }).join('');
        
        container.innerHTML = `
            <h4>Session Earnings</h4>
            ${earningsHtml}
        `;
    } catch (error) {
        console.error('Failed to load session earnings:', error);
        // Don't show error toast for this - it's a non-critical feature
    }
}

async function loadHistorySessionStats(sessionId) {
    try {
        const statsData = await api(`/api/sessions/${sessionId}/stats`);
        const tbody = qs(`#stats-${sessionId}`);
        
        if (!tbody) return;
        
        if (!statsData.players || statsData.players.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" class="table-empty">No games in this session</td></tr>';
            return;
        }
        
        // Render player stats with bar chart
        tbody.innerHTML = statsData.players.map(player => {
            const winPercent = player.winRate;
            const lossPercent = 100 - winPercent;
            
            return `
                <tr>
                    <td>${escapeHtml(player.name)}</td>
                    <td style="text-align: center;">${player.games}</td>
                    <td>
                        <div class="win-rate-bar">
                            <div class="win-rate-bar-segment win-segment" style="width: ${winPercent}%;"></div>
                            <div class="win-rate-bar-segment loss-segment" style="width: ${lossPercent}%;"></div>
                            <div class="win-rate-label">${winPercent}%</div>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        console.error('Failed to load history session stats:', error);
        // Don't show error toast for this - it's a non-critical feature
    }
}

// Switch between carousel tabs in history session view
function switchHistoryTab(sessionId, target) {
    const panes = {
        'history': qs(`#pane-history-${sessionId}`),
        'earnings': qs(`#pane-earnings-${sessionId}`),
        'stats': qs(`#pane-stats-${sessionId}`)
    };
    
    const tabs = qsa(`button[data-session-id="${sessionId}"]`);
    
    // Toggle panes
    Object.entries(panes).forEach(([key, pane]) => {
        if (!pane) return;
        const isActive = key === target;
        pane.classList.toggle('is-active', isActive);
        if (isActive) {
            pane.removeAttribute('hidden');
        } else {
            pane.setAttribute('hidden', '');
        }
    });
    
    // Toggle tabs
    tabs.forEach(tab => {
        const isActive = tab.dataset.tabTarget === target;
        tab.classList.toggle('active', isActive);
        tab.setAttribute('aria-selected', String(isActive));
        tab.tabIndex = isActive ? 0 : -1;
    });
}

async function deleteSession(sessionId, matchCount) {
    const message = matchCount > 0 
        ? `Are you sure you want to delete this session and its ${matchCount} match(es)?`
        : 'Are you sure you want to delete this empty session?';
    
    if (!confirm(message)) {
        return;
    }
    
    try {
        await api(`/api/sessions/${sessionId}`, {
            method: 'DELETE'
        });
        
        toast('Session deleted successfully');
        await loadSessions();
    } catch (error) {
        toast(error.message, 'error');
    }
}


// ==================== Stats Page ====================

// Chart instances registry
const statsCharts = {
    winTop: null,
    winBottom: null,
    moneyTop: null,
    moneyBottom: null,
    pairTop: null,
    pairBottom: null
};

const statsState = {
    isMobile: null,
    barCount: 5,
    raw: null
};

// Phone breakpoint
const statsMq = window.matchMedia('(max-width: 700px)');

// Read CSS variables with fallback
function cssVar(name, fallback) {
    const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return v || fallback;
}

async function initStats() {
    // Determine initial mode
    statsState.isMobile = statsMq.matches;
    statsState.barCount = statsState.isMobile ? 3 : 5;
    
    // React to viewport changes
    statsMq.addEventListener('change', () => {
        statsState.isMobile = statsMq.matches;
        const newCount = statsState.isMobile ? 3 : 5;
        if (newCount !== statsState.barCount) {
            statsState.barCount = newCount;
            if (statsState.raw) {
                renderAllCharts(statsState.raw);
            }
        }
    });
    
    // Initialize Team Partnerships expand button
    initTeamPartnershipsExpand();
    
    await loadStats();
}

async function loadStats() {
    try {
        const [stats, earnings, partnerships] = await Promise.all([
            api('/api/stats'),
            api('/api/earnings'),
            api('/api/partnerships')
        ]);
        
        const shaped = shapeStatsData(stats, earnings, partnerships);
        statsState.raw = shaped;
        renderAllCharts(shaped);
    } catch (error) {
        console.error('Failed to load stats:', error);
        toast('Failed to load statistics', 'error');
    }
}

function shapeStatsData(stats, earnings, partnerships) {
    // Normalize players from stats API (returns array with player, wins, losses, etc.)
    const players = stats.map(s => ({
        name: s.player,
        wins: s.wins || 0,
        losses: s.losses || 0,
        games: s.total_matches || 0,
        winRate: s.total_matches > 0 ? s.wins / s.total_matches : 0,
        net: s.earnings || 0,
        mmr: s.mmr || 1500
    }));
    
    // Normalize earnings (already has net_earnings)
    const earningsMap = {};
    earnings.forEach(e => {
        earningsMap[e.player] = e.net_earnings || 0;
    });
    
    // Update players with earnings
    players.forEach(p => {
        if (earningsMap[p.name] !== undefined) {
            p.net = earningsMap[p.name];
        }
    });
    
    // Normalize partnerships
    const pairs = (partnerships && partnerships.partnerships) ? partnerships.partnerships.map(pp => ({
        key: pp.key,
        players: pp.players,
        label: pp.key,
        wins: pp.wins || 0,
        losses: pp.losses || 0,
        games: pp.games || 0,
        winRate: pp.win_rate || 0,
        earnings: pp.earnings || 0
    })) : [];
    
    return { players, pairs };
}

function topBottomBy(arr, keyFn, count) {
    const cloned = [...arr];
    cloned.sort((a, b) => keyFn(b) - keyFn(a));
    const top = cloned.slice(0, count);
    
    const cloned2 = [...arr];
    cloned2.sort((a, b) => keyFn(a) - keyFn(b));
    const bottom = cloned2.slice(0, count);
    
    return { top, bottom };
}

function computeStatsSlices(raw) {
    const n = statsState.barCount;
    
    const eligiblePlayers = raw.players.filter(p => p.games > 0);
    const wr = topBottomBy(eligiblePlayers, p => p.winRate, n);
    const money = topBottomBy(raw.players, p => p.net, n);
    
    const eligiblePairs = raw.pairs.filter(pp => pp.games > 0);
    const pairs = topBottomBy(eligiblePairs, pp => pp.winRate, n);
    
    return { wr, money, pairs };
}

function setCanvasHeight(canvas, bars, barHeight = 40, padding = 60) {
    canvas.height = (bars * barHeight) + padding;
}

function createHBarChart(canvasId, cfg) {
    const el = document.getElementById(canvasId);
    if (!el) return null;
    const ctx = el.getContext('2d');
    
    if (statsCharts[cfg.chartKey]) {
        statsCharts[cfg.chartKey].destroy();
        statsCharts[cfg.chartKey] = null;
    }
    
    setCanvasHeight(el, cfg.labels.length, cfg.barHeight || 40);
    
    const gridColor = cssVar('--text-muted', 'rgba(128,128,128,0.2)');
    const axisColor = cssVar('--text', '#E6F0EA');
    const bgColor = cfg.color || cssVar('--dg-500', '#40916C');
    
    const options = {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 300 },
        plugins: {
            legend: { display: false },
            tooltip: {
                backgroundColor: cssVar('--gm-700', '#4A5155'),
                titleColor: axisColor,
                bodyColor: axisColor,
                borderColor: gridColor,
                borderWidth: 1,
                padding: 12,
                callbacks: {
                    label: (ctx) => cfg.tooltipLabel(ctx.dataIndex)
                }
            }
        },
        scales: {
            x: {
                beginAtZero: true,
                grid: { color: gridColor },
                ticks: {
                    color: axisColor,
                    callback: cfg.xTickFormatter
                }
            },
            y: {
                grid: { display: false },
                ticks: { color: axisColor }
            }
        }
    };
    
    const data = {
        labels: cfg.labels,
        datasets: [{
            data: cfg.values,
            backgroundColor: cfg.colors || bgColor,
            borderRadius: 6,
            barThickness: 'flex'
        }]
    };
    
    const chart = new Chart(ctx, { type: 'bar', data, options });
    statsCharts[cfg.chartKey] = chart;
    return chart;
}

const fmtPercent = v => `${Math.round(v * 100)}%`;
const fmtCurrency = v => {
    const sign = v < 0 ? '-' : '';
    const abs = Math.abs(v);
    return `${sign}$${abs.toFixed(2)}`;
};

/**
 * Render Player Win Rates as a win-rate-bar list
 * @param {Array} players - Array of player stats with {name, wins, losses, games, winRate}
 */
function renderPlayerWinRates(players) {
    const container = qs('#player-winrates-list');
    if (!container) return;
    
    // Clear container
    container.innerHTML = '';
    
    // Filter players with at least 1 game
    const eligiblePlayers = players.filter(p => p.games > 0);
    
    // Sort by win rate (descending), then by games (descending) as tiebreaker
    eligiblePlayers.sort((a, b) => {
        if (b.winRate !== a.winRate) return b.winRate - a.winRate;
        return b.games - a.games;
    });
    
    if (eligiblePlayers.length === 0) {
        container.innerHTML = '<div style="color: var(--text-muted); padding: 1rem; text-align: center;">No player data available</div>';
        return;
    }
    
    // Render each player as a row
    eligiblePlayers.forEach(player => {
        const winPercent = Math.round(player.winRate * 100);
        const lossPercent = 100 - winPercent;
        
        // Create row
        const row = document.createElement('div');
        row.className = 'win-rate-row';
        
        // Name cell with MMR
        const nameCell = document.createElement('div');
        nameCell.className = 'name';
        const mmr = player.mmr || 1500;
        nameCell.innerHTML = `
            <span class="mmr-badge">${Math.round(mmr)}</span>
            ${escapeHtml(player.name)}
        `;
        nameCell.title = `${player.name} - MMR: ${Math.round(mmr)}`; // Tooltip
        
        // Games cell
        const gamesCell = document.createElement('div');
        gamesCell.className = 'games';
        gamesCell.textContent = player.games;
        
        // Bar container
        const barContainer = document.createElement('div');
        barContainer.className = 'bar-container';
        
        // Win rate bar
        const barWrap = document.createElement('div');
        barWrap.className = 'win-rate-bar';
        
        // Win segment
        const winSeg = document.createElement('div');
        winSeg.className = 'win-rate-bar-segment win-segment';
        winSeg.style.width = `${winPercent}%`;
        
        // Loss segment
        const lossSeg = document.createElement('div');
        lossSeg.className = 'win-rate-bar-segment loss-segment';
        lossSeg.style.width = `${lossPercent}%`;
        
        // Label
        const label = document.createElement('div');
        label.className = 'win-rate-label';
        label.textContent = `${winPercent}%`;
        
        // Assemble bar
        barWrap.appendChild(winSeg);
        barWrap.appendChild(lossSeg);
        barWrap.appendChild(label);
        barContainer.appendChild(barWrap);
        
        // Assemble row
        row.appendChild(nameCell);
        row.appendChild(gamesCell);
        row.appendChild(barContainer);
        
        container.appendChild(row);
    });
}

/**
 * Render Team Partnerships as expandable win-rate-bar list
 * Sorted by win rate (descending)
 */
let partnershipVisibleCount = 5;
let allPartnerships = [];

function renderTeamPartnerships(pairs) {
    const container = qs('#team-partnerships-list');
    const moreBtn = qs('#team-partnerships-more');
    if (!container) return;
    
    // Store partnerships globally for expand/collapse
    allPartnerships = pairs;
    
    // Clear container
    container.innerHTML = '';
    
    // Filter partnerships with at least 4 games
    const eligiblePairs = pairs.filter(p => p.games >= 4);
    
    // Sort by win rate (descending), then by games as tiebreaker
    eligiblePairs.sort((a, b) => {
        if (b.winRate !== a.winRate) return b.winRate - a.winRate;
        return b.games - a.games;
    });
    
    if (eligiblePairs.length === 0) {
        container.innerHTML = '<div style="color: var(--text-muted); padding: 1rem; text-align: center;">No partnership data available</div>';
        if (moreBtn) moreBtn.hidden = true;
        return;
    }
    
    // Determine how many to show
    const showCount = Math.min(partnershipVisibleCount, eligiblePairs.length);
    const visiblePairs = eligiblePairs.slice(0, showCount);
    
    // Render visible partnerships
    visiblePairs.forEach(pair => {
        const winPercent = Math.round(pair.winRate * 100);
        const lossPercent = 100 - winPercent;
        
        // Create row
        const row = document.createElement('div');
        row.className = 'win-rate-row';
        
        // Name cell (partnership label)
        const nameCell = document.createElement('div');
        nameCell.className = 'name';
        nameCell.textContent = pair.label;
        nameCell.title = pair.label;
        
        // Games cell
        const gamesCell = document.createElement('div');
        gamesCell.className = 'games';
        gamesCell.textContent = pair.games;
        
        // Bar container
        const barContainer = document.createElement('div');
        barContainer.className = 'bar-container';
        
        // Win rate bar
        const barWrap = document.createElement('div');
        barWrap.className = 'win-rate-bar';
        
        // Win segment
        const winSeg = document.createElement('div');
        winSeg.className = 'win-rate-bar-segment win-segment';
        winSeg.style.width = `${winPercent}%`;
        
        // Loss segment
        const lossSeg = document.createElement('div');
        lossSeg.className = 'win-rate-bar-segment loss-segment';
        lossSeg.style.width = `${lossPercent}%`;
        
        // Label
        const label = document.createElement('div');
        label.className = 'win-rate-label';
        label.textContent = `${winPercent}%`;
        
        // Assemble bar
        barWrap.appendChild(winSeg);
        barWrap.appendChild(lossSeg);
        barWrap.appendChild(label);
        barContainer.appendChild(barWrap);
        
        // Assemble row
        row.appendChild(nameCell);
        row.appendChild(gamesCell);
        row.appendChild(barContainer);
        
        container.appendChild(row);
    });
    
    // Show/hide more button
    if (moreBtn) {
        if (eligiblePairs.length <= 5) {
            // Hide button if 5 or fewer partnerships
            moreBtn.hidden = true;
        } else if (showCount >= eligiblePairs.length) {
            // All visible - hide button
            moreBtn.hidden = true;
        } else {
            // More to show
            moreBtn.hidden = false;
        }
    }
}

/**
 * Handle Show More button for partnerships
 */
function initTeamPartnershipsExpand() {
    const moreBtn = qs('#team-partnerships-more');
    if (!moreBtn) return;
    
    moreBtn.addEventListener('click', () => {
        partnershipVisibleCount += 5;
        // Re-render with expanded count
        renderTeamPartnerships(allPartnerships);
    });
}

/**
 * Render Player Earnings as a simple list
 * @param {Array} players - Array of player stats with {name, net, games}
 */
function renderPlayerEarnings(players) {
    const container = qs('#player-earnings-list');
    if (!container) return;
    
    // Clear container
    container.innerHTML = '';
    
    // Filter out players with no games, then sort by net earnings (descending)
    const sortedPlayers = players
        .filter(p => p.games > 0)
        .sort((a, b) => b.net - a.net);
    
    if (sortedPlayers.length === 0) {
        container.innerHTML = '<div style="color: var(--text-muted); padding: 1rem; text-align: center;">No earnings data available</div>';
        return;
    }
    
    // Render each player
    sortedPlayers.forEach(player => {
        const earningsFormatted = formatEarnings(player.net);
        
        const item = document.createElement('div');
        item.className = 'earnings-item';
        
        const nameSpan = document.createElement('span');
        nameSpan.className = 'earnings-player';
        nameSpan.textContent = player.name;
        
        const amountSpan = document.createElement('span');
        amountSpan.className = `earnings-amount ${earningsFormatted.className}`;
        amountSpan.textContent = earningsFormatted.text;
        
        item.appendChild(nameSpan);
        item.appendChild(amountSpan);
        container.appendChild(item);
    });
}

function renderAllCharts(raw) {
    // Render Player Win Rates as win-rate-bar list
    renderPlayerWinRates(raw.players);
    
    // Render Player Earnings as simple list
    renderPlayerEarnings(raw.players);
    
    // Render Team Partnerships as expandable win-rate-bar list
    renderTeamPartnerships(raw.pairs);
}


// ==================== Helper Functions ====================

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ==================== Drag to Scroll for Match History ====================

function initDragScroll() {
    const matchHistoryScroll = document.querySelector('.card--history .table-scroll');
    
    if (!matchHistoryScroll) return;
    
    let isDown = false;
    let startY;
    let scrollTop;
    
    matchHistoryScroll.addEventListener('mousedown', (e) => {
        isDown = true;
        startY = e.pageY - matchHistoryScroll.offsetTop;
        scrollTop = matchHistoryScroll.scrollTop;
    });
    
    matchHistoryScroll.addEventListener('mouseleave', () => {
        isDown = false;
    });
    
    matchHistoryScroll.addEventListener('mouseup', () => {
        isDown = false;
    });
    
    matchHistoryScroll.addEventListener('mousemove', (e) => {
        if (!isDown) return;
        e.preventDefault();
        const y = e.pageY - matchHistoryScroll.offsetTop;
        const walk = (y - startY) * 2; // Scroll speed multiplier
        matchHistoryScroll.scrollTop = scrollTop - walk;
    });
}

// ==================== Courts Selector ====================

/**
 * Initialize courts selector tabs
 * Shows/hides court rows based on user selection (1, 2, or 3 courts)
 * Persists selection to localStorage for session continuity
 */
function initCourtsSelector() {
    const courtsTabs = qsa('.courts-tab');
    const courtRows = [
        qs('#court-1-row'),
        qs('#court-2-row'),
        qs('#court-3-row')
    ];
    
    // Verify elements exist
    if (courtsTabs.length === 0 || !courtRows[0]) {
        console.warn('Courts selector: Elements not found');
        return;
    }
    
    /**
     * Set the number of visible courts
     * @param {number} count - Number of courts to display (1-3)
     */
    function setCourtCount(count) {
        const n = Math.max(1, Math.min(3, count)); // Clamp to 1-3
        
        // Show/hide court rows
        courtRows.forEach((row, index) => {
            if (row) {
                row.classList.toggle('court-row--hidden', index >= n);
            }
        });
        
        // Update tab states
        courtsTabs.forEach(tab => {
            const tabCourts = parseInt(tab.dataset.courts, 10);
            const isActive = tabCourts === n;
            tab.classList.toggle('is-active', isActive);
            tab.setAttribute('aria-selected', String(isActive));
        });
        
        // Persist to localStorage
        try {
            localStorage.setItem('courtsCount', String(n));
        } catch (e) {
            console.warn('Failed to save courts count to localStorage:', e);
        }
    }
    
    // Wire up click handlers
    courtsTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const count = parseInt(tab.dataset.courts, 10);
            setCourtCount(count);
        });
        
        // Keyboard accessibility
        tab.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                const count = parseInt(tab.dataset.courts, 10);
                setCourtCount(count);
            }
        });
    });
    
    // Initialize with saved value or default to 2
    let initialCount = 2;
    try {
        const saved = localStorage.getItem('courtsCount');
        if (saved) {
            initialCount = parseInt(saved, 10);
        }
    } catch (e) {
        console.warn('Failed to load courts count from localStorage:', e);
    }
    
    setCourtCount(initialCount);
}

// ==================== Carousel Tabs ====================

function initCarouselTabs() {
    const tabs = qsa('.card-header-tabs .tab-item');
    const panes = {
        'match-history': qs('#pane-match-history'),
        'player-earnings': qs('#pane-player-earnings'),
        'partnership-stats': qs('#pane-partnership-stats')
    };

    // Verify all panes exist
    if (!panes['match-history'] || !panes['player-earnings'] || !panes['partnership-stats']) {
        console.warn('Carousel tabs: One or more panes not found');
        return;
    }

    function activate(target) {
        // Toggle panes
        Object.entries(panes).forEach(([key, pane]) => {
            const isActive = key === target;
            pane.classList.toggle('is-active', isActive);
            if (isActive) {
                pane.removeAttribute('hidden');
            } else {
                pane.setAttribute('hidden', '');
            }
        });

        // Toggle tabs
        tabs.forEach(tab => {
            const isActive = tab.dataset.tabTarget === target;
            tab.classList.toggle('active', isActive);
            tab.setAttribute('aria-selected', String(isActive));
            tab.tabIndex = isActive ? 0 : -1;
        });
    }

    // Wire up clicks
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            activate(tab.dataset.tabTarget);
        });
    });

    // Default to Match History on load
    activate('match-history');
}

// ==================== Mobile Navigation ====================

function initMobileNav() {
    const sidenav = document.getElementById('mobile-sidenav');

    if (!sidenav) return;

    // Mobile nav is now always visible - no toggle needed
    // Just ensure it's marked as visible for accessibility
    sidenav.setAttribute('aria-hidden', 'false');
}

// ==================== Page Router ====================

document.addEventListener('DOMContentLoaded', () => {
    const page = document.body.dataset.page;
    
    // Initialize mobile navigation on all pages
    initMobileNav();
    
    const pageInitializers = {
        'dashboard': initDashboard,
        'players': initPlayers,
        'matchups': initMatchups,
        'history': initHistory,
        'stats': initStats
    };
    
    if (pageInitializers[page]) {
        pageInitializers[page]();
    }
    
    // Initialize drag scroll for matchups page
    if (page === 'matchups') {
        initDragScroll();
        initCarouselTabs();
        initCourtsSelector();
    }
});
