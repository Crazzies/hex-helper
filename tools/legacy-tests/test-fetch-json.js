const axios = require('axios');
const fs = require('fs');

async function testFetch() {
    const url = 'https://hextech.dtodo.cn/data/augments-stats-raw.json';
    const headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://hextech.dtodo.cn/'
    };
    try {
        console.log('Fetching ' + url);
        const resp = await axios.get(url, { headers, timeout: 10000 });
        console.log('Success! Data length: ' + resp.data.length);
        fs.writeFileSync('augments_test.json', JSON.stringify(resp.data.slice(0, 5), null, 2));
    } catch (e) {
        console.log('Failed: ' + e.message);
    }
}

testFetch();
