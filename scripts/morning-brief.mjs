#!/usr/bin/env node

/**
 * Morning Brief Generator
 * 
 * Sends a comprehensive morning brief to Telegram at 7:00 AM MT with:
 * - Weather and forecast for Golden, CO
 * - Top 5 news stories
 * - Task list for today
 * - Proactive suggestions
 * 
 * Usage: node scripts/morning-brief.mjs
 * 
 * Scheduled via cron: 0 7 * * * (7:00 AM Mountain Time)
 */

import fs from 'fs';
import https from 'https';
import http from 'http';

const TELEGRAM_BOT_TOKEN = '8565359157:AAE3cA0Tn2OE62K2eaXiXYr1SFqAFkNtzMQ';
const TELEGRAM_CHAT_ID = '5316436116';
const WEATHER_LOCATION = 'Golden, CO';
const LOG_PATH = './logs/morning-brief.log';

// Ensure logs directory exists
if (!fs.existsSync('./logs')) {
  fs.mkdirSync('./logs', { recursive: true });
}

function log(message) {
  const timestamp = new Date().toISOString();
  const logMessage = `[${timestamp}] ${message}`;
  console.log(logMessage);
  fs.appendFileSync(LOG_PATH, logMessage + '\n');
}

function makeRequest(url, method = 'GET') {
  return new Promise((resolve, reject) => {
    const urlObj = new URL(url);
    const isHttps = urlObj.protocol === 'https:';
    const requester = isHttps ? https : http;

    const options = {
      method,
      headers: {
        'User-Agent': 'OpenClaw-Morning-Brief/1.0',
      },
    };

    const req = requester.request(url, options, (res) => {
      let data = '';
      res.on('data', (chunk) => {
        data += chunk;
      });
      res.on('end', () => {
        try {
          resolve({
            status: res.statusCode,
            data: JSON.parse(data),
          });
        } catch (e) {
          resolve({
            status: res.statusCode,
            data: data,
          });
        }
      });
    });

    req.on('error', reject);
    req.end();
  });
}

async function fetchWeather() {
  try {
    log('Fetching weather...');
    // Using wttr.in API for weather (no API key needed)
    const response = await makeRequest(`https://wttr.in/Golden,CO?format=j1`);
    
    if (response.status === 200 && response.data?.current_condition) {
      const current = response.data.current_condition[0];
      const forecast = response.data.weather?.[0]?.hourly?.[0] || {};
      
      return {
        temp: current.temp_C,
        condition: current.weatherDesc?.[0]?.value || 'Unknown',
        feelsLike: current.FeelsLikeC,
        windSpeed: current.windspeedKmph,
        humidity: current.humidity,
        icon: getWeatherEmoji(current.weatherDesc?.[0]?.value || ''),
      };
    }
  } catch (error) {
    log(`⚠ Weather fetch failed: ${error.message}`);
  }
  return null;
}

function getWeatherEmoji(condition) {
  if (condition.includes('sunny') || condition.includes('clear')) return '☀️';
  if (condition.includes('cloudy') || condition.includes('overcast')) return '☁️';
  if (condition.includes('rain')) return '🌧️';
  if (condition.includes('snow')) return '❄️';
  if (condition.includes('wind')) return '💨';
  return '🌤️';
}

async function fetchTopNews() {
  try {
    log('Fetching top news...');
    // Using a simple news API or RSS feed
    // For demo, we'll fetch from a tech news source
    const response = await makeRequest(`https://hacker-news.firebaseio.com/v0/topstories.json`);
    
    if (response.status === 200 && Array.isArray(response.data)) {
      const storyIds = response.data.slice(0, 5);
      const stories = [];
      
      for (const id of storyIds) {
        try {
          const storyRes = await makeRequest(`https://hacker-news.firebaseio.com/v0/item/${id}.json`);
          if (storyRes.status === 200 && storyRes.data?.title) {
            stories.push({
              title: storyRes.data.title,
              url: storyRes.data.url,
              score: storyRes.data.score,
            });
          }
          if (stories.length >= 5) break;
        } catch (e) {
          continue;
        }
      }
      
      return stories;
    }
  } catch (error) {
    log(`⚠ News fetch failed: ${error.message}`);
  }
  
  return [
    { title: 'Market opens today', url: '#', score: 0 },
    { title: 'Tech industry update', url: '#', score: 0 },
    { title: 'AI developments continue', url: '#', score: 0 },
    { title: 'Trading alerts active', url: '#', score: 0 },
    { title: 'Platform updates rolling out', url: '#', score: 0 },
  ];
}

function getTodaysTasks() {
  try {
    const tasks = JSON.parse(fs.readFileSync('./tasks.json', 'utf-8'));
    const today = new Date().toISOString().split('T')[0];
    
    const todaysTasks = tasks.tasks.filter(t => 
      t.dueDate === today && !t.completed
    );
    
    return todaysTasks.length > 0 ? todaysTasks : tasks.tasks.filter(t => !t.completed).slice(0, 3);
  } catch (error) {
    log(`⚠ Tasks fetch failed: ${error.message}`);
    return [];
  }
}

function getProactiveSuggestions() {
  // Based on active projects in MEMORY.md
  const suggestions = [];
  
  // Check date for context
  const today = new Date();
  const dayOfWeek = today.getDay();
  const isMonday = dayOfWeek === 1;
  const isTuesday = dayOfWeek === 2;
  const isFriday = dayOfWeek === 5;
  
  // Trading-related
  if (isMonday) {
    suggestions.push('🚀 Launch trading system today at 7:30 AM - market opens at 9:30 AM');
  } else if (today.getHours() < 14) {
    suggestions.push('📊 Monitor watchlist during trading hours (7:30 AM - 2:00 PM)');
  }
  
  // Kinlet GTM
  if (dayOfWeek >= 1 && dayOfWeek <= 4) { // Mon-Thu
    suggestions.push('🎯 Execute one Kinlet outreach task (Reddit post or DM batch)');
  }
  
  // Job search
  if (isTuesday) {
    suggestions.push('💼 Request warm intros for top 5 target companies');
  }
  if (isFriday) {
    suggestions.push('📋 Review week 1 job search progress & plan phase 2');
  }
  
  // Content
  suggestions.push('📝 Consider recording voice notes for research or market insights');
  
  return suggestions.slice(0, 3);
}

function formatBrief(weather, news, tasks, suggestions) {
  let brief = '🌅 *Good Morning, Ryan*\n\n';
  
  // Weather section
  if (weather) {
    brief += `*☀️ Weather - Golden, CO*\n`;
    brief += `${weather.icon} ${weather.temp}°C (feels like ${weather.feelsLike}°C)\n`;
    brief += `${weather.condition} | Wind: ${weather.windSpeed} km/h | Humidity: ${weather.humidity}%\n\n`;
  }
  
  // News section
  brief += `*📰 Top Stories*\n`;
  news.slice(0, 5).forEach((story, idx) => {
    brief += `${idx + 1}. ${story.title}\n`;
  });
  brief += '\n';
  
  // Tasks section
  brief += `*✅ Today's Tasks*\n`;
  if (tasks.length > 0) {
    tasks.forEach(task => {
      const priority = task.priority === 'critical' ? '🔴' : task.priority === 'high' ? '🟡' : '⚪';
      brief += `${priority} ${task.title} (${task.project})\n`;
    });
  } else {
    brief += 'No tasks scheduled. Suggest some work first!\n';
  }
  brief += '\n';
  
  // Suggestions section
  brief += `*💡 Suggested Focus Today*\n`;
  suggestions.forEach(suggestion => {
    brief += `${suggestion}\n`;
  });
  brief += '\n';
  
  brief += `_Generated: ${new Date().toLocaleTimeString('en-US', { timeZone: 'America/Denver' })} MT_`;
  
  return brief;
}

async function sendTelegram(message) {
  try {
    log('Sending to Telegram...');
    
    const payload = JSON.stringify({
      chat_id: TELEGRAM_CHAT_ID,
      text: message,
      parse_mode: 'Markdown',
    });
    
    const options = {
      hostname: 'api.telegram.org',
      path: `/bot${TELEGRAM_BOT_TOKEN}/sendMessage`,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(payload),
      },
    };
    
    return new Promise((resolve, reject) => {
      const req = https.request(options, (res) => {
        let data = '';
        res.on('data', (chunk) => {
          data += chunk;
        });
        res.on('end', () => {
          try {
            const result = JSON.parse(data);
            if (result.ok) {
              log('✓ Telegram message sent successfully');
              resolve(true);
            } else {
              log(`✗ Telegram error: ${result.description}`);
              resolve(false);
            }
          } catch (e) {
            resolve(false);
          }
        });
      });
      
      req.on('error', reject);
      req.write(payload);
      req.end();
    });
  } catch (error) {
    log(`✗ Telegram send failed: ${error.message}`);
    return false;
  }
}

async function sendEmail(briefText, plaintext) {
  try {
    log('Sending to email...');
    
    // Get Resend API key from environment
    const resendApiKey = process.env.RESEND_API_KEY;
    if (!resendApiKey) {
      log('⚠ RESEND_API_KEY not set, skipping email delivery');
      return false;
    }
    
    // Format email body (convert markdown to HTML-friendly text)
    const htmlBody = plaintext
      .replace(/\*\*/g, '')
      .replace(/\*/g, '')
      .replace(/\n/g, '<br>')
      .split('_Generated')[0];
    
    const payload = JSON.stringify({
      from: 'onboarding@resend.dev',
      to: 'ryanwinzenburg@gmail.com',
      subject: `Morning Brief - ${new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}`,
      html: `<pre style="font-family: monospace; white-space: pre-wrap;">${htmlBody}</pre><br><small>Generated: ${new Date().toLocaleTimeString('en-US', { timeZone: 'America/Denver' })} MT</small>`,
    });
    
    const options = {
      hostname: 'api.resend.com',
      path: '/emails',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${resendApiKey}`,
        'Content-Length': Buffer.byteLength(payload),
      },
    };
    
    return new Promise((resolve, reject) => {
      const req = https.request(options, (res) => {
        let data = '';
        res.on('data', (chunk) => {
          data += chunk;
        });
        res.on('end', () => {
          try {
            const result = JSON.parse(data);
            if (res.statusCode === 200 || result.id) {
              log('✓ Email sent successfully');
              resolve(true);
            } else {
              log(`✗ Email error: ${result.message || 'Unknown error'}`);
              resolve(false);
            }
          } catch (e) {
            resolve(false);
          }
        });
      });
      
      req.on('error', reject);
      req.write(payload);
      req.end();
    });
  } catch (error) {
    log(`✗ Email send failed: ${error.message}`);
    return false;
  }
}

async function main() {
  try {
    log('===== Morning Brief Start =====');
    
    // Fetch all data in parallel
    const [weather, news, tasks, suggestions] = await Promise.all([
      fetchWeather(),
      fetchTopNews(),
      Promise.resolve(getTodaysTasks()),
      Promise.resolve(getProactiveSuggestions()),
    ]);
    
    // Format brief
    const brief = formatBrief(weather, news, tasks, suggestions);
    
    // Send to both Telegram and Email
    const [telegramSuccess, emailSuccess] = await Promise.all([
      sendTelegram(brief),
      sendEmail(brief, brief),
    ]);
    
    if (telegramSuccess || emailSuccess) {
      log('===== Morning Brief Complete =====');
    } else {
      log('⚠ Warning: Brief generated but delivery channels failed');
    }
  } catch (error) {
    log(`✗ Fatal error: ${error.message}`);
    process.exit(1);
  }
}

main();
