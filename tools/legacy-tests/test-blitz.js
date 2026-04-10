const { app } = require('electron');
const fs = require('fs');
const scraper = require('./src/main/services/scraper-service');

app.whenReady().then(async () => {
    console.log('--- [BLITZ API TEST] Starting Katarina (ID: 55) ---');
    try {
        const result = await scraper.scrapeHeroDetailFromBlitz(55);
        if (result) {
            console.log('SUCCESS! Extracted full build from Blitz API.');
            console.log('Items Count:', result.situationalItems.length);
            console.log('Prismatic (Top 3):', result.prismatic.slice(0, 3).map(h => `${h.name} (${h.winRate})`).join(', '));
            
            if (!fs.existsSync('cache/hero-builds')) fs.mkdirSync('cache/hero-builds', { recursive: true });
            fs.writeFileSync('cache/hero-builds/55.json', JSON.stringify(result, null, 2));
        } else {
            console.log('FAILED! API returned nothing.');
        }
    } catch (e) {
        console.error('CRASH:', e.message);
    } finally {
        app.quit();
    }
});
