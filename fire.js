const WIDTH=300;
const HEIGHT=200;
const energyDecay=0.4;

const states = {
	UNBURNT: Symbol("UNBURNT"),
	ONFIRE: Symbol("ONFIRE"),
	BURNT: Symbol("BURNT"),
}

const defaults = {
	GRASS: {
		totalBurnTime: 10,
		heat: 10,
		energyOfCombustion: 11,
		color: {
			0: "#00b515",
			1: "#f0b22e",
			3: "#f77d20",
			7: "#915a30",
			10:"#615044",
		},
		nextColorAt: {
			0: 1,
			1: 3,
			3: 7,
			7: 10
		}
	},
	BRUSH: {
		totalBurnTime: 25,
		heat: 60,
		energyOfCombustion: 130,
		color: {
			0: "#00800F",
			1: "#E28B00",
			6: "#F77020",
			15: "#F75C20",
			18: "#5D3A1F",
			25: "#534439",
		},
		nextColorAt: {
			0: 1,
			1: 6,
			6: 15,
			15: 18,
			18: 25
		}
	}
};

const getCellType = function(i, j) {
	const threshold = 0.75 * ((i/HEIGHT) * (j/WIDTH))**0.4;
	const m = Math.random();
	if (m <= threshold) {
		return "BRUSH";
	}
	return "GRASS";
}

const gameDiv = document.getElementById("field");
const game = [];
// seed
for (var i = 0; i < HEIGHT; i++) {
	game.push([]);
	gameDiv.appendChild(document.createElement("div"))
	gameDiv.children[i].className = "row";
	for (var j = 0; j < WIDTH; j++) {
		const type = getCellType(i, j);
		gameDiv.children[i].appendChild(document.createElement("div"))
		gameDiv.children[i].children[j].className = "cell";
		game[i].push({
			type: type,
			nextTimeBurning: 0,
			timeBurning: 0,
			heatReceived: 0,
			energyOfCombustion: defaults[type].energyOfCombustion * (0.75+Math.random()*0.5),
			color: defaults[type].color[0],
			nextColorAt: defaults[type].nextColorAt[0],
			state: states.UNBURNT,
			div: gameDiv.children[i].children[j],
		});
		gameDiv.children[i].children[j].onclick = function(c) {
			return function() {
				c.state = states.ONFIRE;
			};
		}(game[i][j]);
	}
}

const tick = function() {
	for (var i = 0; i < game.length; i++) {
		for (var j = 0; j < game[i].length; j++) {
			const c = game[i][j];
			if (c.state === states.ONFIRE) {
				c.nextTimeBurning = c.timeBurning + 1;

				if (c.timeBurning >= defaults[c.type].totalBurnTime) {
					c.nextState = states.BURNT;
				}

				if (c.nextTimeBurning === c.nextColorAt) {
					c.color = defaults[c.type].color[c.nextTimeBurning];
					c.nextColorAt = defaults[c.type].nextColorAt[c.nextTimeBurning];
				}
				continue;
			}

			c.heatReceived = c.heatReceived * energyDecay;

			// calc neighbor heat received
			let heatReceived = c.heatReceived;
			for (var m = Math.max(0, i - 1); m <= Math.min(game.length-1, i+1); m++) {
				for (var n = Math.max(0, j - 1); n <= Math.min(game[i].length-1, j+1); n++) {
					if (game[m][n].state === states.ONFIRE) {
						heatReceived = heatReceived + defaults[game[m][n].type].heat * (0.65+Math.random()*0.45);
					}
				}
			}
			c.heatReceived = heatReceived;
			if (c.heatReceived > c.energyOfCombustion) {
				c.nextState = states.ONFIRE;
			}
		}
	}
};

const render = function() {
	for (var i = 0; i < game.length; i++) {
		for (var j = 0; j < game[i].length; j++) {
			const c = game[i][j];
			// mutate
			c.timeBurning = c.nextTimeBurning;
			if (c.nextState) {
				c.state = c.nextState;
			}
			//

			if (c.prevColor !== c.color) {
				c.div.style.background = c.color;
				c.prevColor = c.color;
			}
		}
	}
};

render();
const int = setInterval(function() {
	tick();
	render();
}, 100);

const neighborstates = function(i, j) {
	for (var m = Math.max(0, i - 1); m <= Math.min(game.length-1, i+1); m++) {
		for (var n = Math.max(0, j - 1); n <= Math.min(game[i].length-1, j+1); n++) {
			if (game[m][n].state === states.ONFIRE) {
				console.log({m,
					n,
					heatMin: defaults[game[m][n].type].heat*0.65,
					heatMax: defaults[game[m][n].type].heat*1.1
				})
			}
		}
	}
};
