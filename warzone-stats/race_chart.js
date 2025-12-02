// Race Chart Animation
let raceTimeline = [];
let raceCurrentFrame = 0;
let raceAnimationId = null;

function buildRaceTimeline() {
    const sortedGames = [...gamesData.games]
        .filter(g => g.state === 'Finished' && g.created)
        .sort((a, b) => new Date(a.created) - new Date(b.created));

    if (sortedGames.length === 0) {
        raceTimeline = [];
        return;
    }

    const playerWins = {};
    raceTimeline = [];

    sortedGames.forEach(game => {
        game.players.forEach(player => {
            if (!playerWins[player.name]) {
                playerWins[player.name] = 0;
            }
            if (player.state === 'Won') {
                playerWins[player.name]++;
            }
        });

        raceTimeline.push({
            date: new Date(game.created),
            standings: { ...playerWins }
        });
    });
}

function renderRaceChart(frameIndex) {
    const container = document.getElementById('raceChart');
    const currentDate = document.getElementById('currentDate');

    if (raceTimeline.length === 0) {
        container.innerHTML = '<p style="text-align:center;color:#aaa">No game history available</p>';
        return;
    }

    const frame = raceTimeline[frameIndex];
    currentDate.textContent = frame.date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
    }) + ` (Game ${frameIndex + 1}/${raceTimeline.length})`;

    const sorted = Object.entries(frame.standings)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10);

    const maxWins = sorted[0]?.[1] || 1;
    const ROW_HEIGHT = 43;

    // Get existing bars
    const existingBars = new Map();
    container.querySelectorAll('.race-bar-container').forEach(bar => {
        existingBars.set(bar.dataset.player, bar);
    });

    // Update or create bars
    sorted.forEach(([player, wins], targetIndex) => {
        const width = Math.max(1, (wins / maxWins * 100));
        const targetY = targetIndex * ROW_HEIGHT;
        let barContainer = existingBars.get(player);

        if (!barContainer) {
            barContainer = document.createElement('div');
            barContainer.className = 'race-bar-container';
            barContainer.dataset.player = player;
            barContainer.style.transform = `translateY(${targetY}px)`;
            barContainer.innerHTML = `
                <div class="race-player-name">${player}</div>
                <div class="race-bar-wrapper">
                    <div class="race-bar" style="width: 1%">
                        <span class="race-bar-value">0</span>
                    </div>
                </div>
            `;
            container.appendChild(barContainer);
        }

        // Update bar width and value
        const bar = barContainer.querySelector('.race-bar');
        const value = barContainer.querySelector('.race-bar-value');
        bar.style.width = width + '%';
        value.textContent = wins;

        // Animate to new position
        barContainer.style.transform = `translateY(${targetY}px)`;

        existingBars.delete(player);
    });

    // Remove bars no longer in top 10
    existingBars.forEach(bar => bar.remove());
}

function setupRaceControls() {
    const playBtn = document.getElementById('playBtn');
    const pauseBtn = document.getElementById('pauseBtn');
    const resetBtn = document.getElementById('resetBtn');
    const speedSelect = document.getElementById('speedSelect');

    playBtn.addEventListener('click', () => {
        if (raceAnimationId) return;

        raceAnimationId = setInterval(() => {
            raceCurrentFrame++;
            if (raceCurrentFrame >= raceTimeline.length) {
                raceCurrentFrame = raceTimeline.length - 1;
                clearInterval(raceAnimationId);
                raceAnimationId = null;
            }
            renderRaceChart(raceCurrentFrame);
        }, parseInt(speedSelect.value));
    });

    pauseBtn.addEventListener('click', () => {
        if (raceAnimationId) {
            clearInterval(raceAnimationId);
            raceAnimationId = null;
        }
    });

    resetBtn.addEventListener('click', () => {
        if (raceAnimationId) {
            clearInterval(raceAnimationId);
            raceAnimationId = null;
        }
        raceCurrentFrame = 0;
        renderRaceChart(0);
    });

    speedSelect.addEventListener('change', (e) => {
        const newSpeed = parseInt(e.target.value);
        if (raceAnimationId) {
            clearInterval(raceAnimationId);
            raceAnimationId = setInterval(() => {
                raceCurrentFrame++;
                if (raceCurrentFrame >= raceTimeline.length) {
                    raceCurrentFrame = raceTimeline.length - 1;
                    clearInterval(raceAnimationId);
                    raceAnimationId = null;
                }
                renderRaceChart(raceCurrentFrame);
            }, newSpeed);
        }
    });
}
