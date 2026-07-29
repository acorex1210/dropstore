(() => {
  function log(msg) {
    console.log(`[WhatsApp Leads] ${msg}`);
  }

  function getAllChatItems() {
    const selectors = [
      'div[role="listitem"]',
      'div[data-testid="cell-frame-container"]',
      'div._ak7u',
      'div._aigw'
    ];

    for (const sel of selectors) {
      const items = document.querySelectorAll(sel);
      if (items.length > 0) {
        log(`Found ${items.length} chats with selector: ${sel}`);
        return Array.from(items);
      }
    }

    log('No chats found with any selector, trying aria-label fallback');
    const allDivs = document.querySelectorAll('div[role="listitem"]');
    if (allDivs.length > 0) {
      log(`Found ${allDivs.length} role=listitem elements`);
      return Array.from(allDivs);
    }

    log('Fallback: scanning all divs with click handlers in sidebar');
    const sidebar = document.querySelector('div[tabindex="-1"]') ||
                    document.querySelector('#side') ||
                    document.querySelector('div[role="complementary"]');
    if (sidebar) {
      const items = sidebar.querySelectorAll('div[role="listitem"]');
      log(`Sidebar fallback: found ${items.length} items`);
      return Array.from(items);
    }

    return [];
  }

  function extractNumber(chatItem) {
    const spansWithTitle = chatItem.querySelectorAll('span[title]');
    for (const span of spansWithTitle) {
      const title = span.getAttribute('title') || '';
      const phoneMatch = title.match(/^[\+]?\d[\d\s\-\(\)]{6,14}\d$/);
      if (phoneMatch) {
        return title.trim();
      }
    }

    const ariaLabel = chatItem.getAttribute('aria-label') || '';
    const ariaMatch = ariaLabel.match(/[\+]?\d[\d\s\-\(\)]{6,14}\d/);
    if (ariaMatch) {
      return ariaMatch[0].trim();
    }

    const allText = chatItem.textContent || '';
    const phoneMatch = allText.match(/\+?\d[\d\s\-\(\)]{7,15}/);
    if (phoneMatch) {
      return phoneMatch[0].trim();
    }

    return null;
  }

  function normalizeNumber(num) {
    return num.replace(/[\s\-\(\)]/g, '');
  }

  function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  function getVisibleMessages() {
    const selectors = [
      'div.message-in, div.message-out',
      'div[data-testid="msg-container"]',
      'div._2nmDZ',
      'div._1gJgL'
    ];

    for (const sel of selectors) {
      const msgs = document.querySelectorAll(sel);
      if (msgs.length > 0) {
        log(`Found ${msgs.length} messages with: ${sel}`);
        return Array.from(msgs);
      }
    }

    const main = document.querySelector('div[role="main"]');
    if (main) {
      const msgs = main.querySelectorAll('div[class*="message"]');
      log(`Main fallback: found ${msgs.length} message elements`);
      return Array.from(msgs);
    }

    return [];
  }

  function getMessageText(messageEl) {
    const selectors = [
      'span.selectable-text',
      'span._ao3e',
      'div._ak1r span',
      'span[dir="auto"]',
      'span[class*="selectable"]'
    ];

    for (const sel of selectors) {
      const els = messageEl.querySelectorAll(sel);
      for (const el of els) {
        const text = el.textContent?.trim();
        if (text && text.length > 0) {
          return text;
        }
      }
    }

    return messageEl.textContent?.trim() || '';
  }

  async function scanSingleChat(chatItem, keywords) {
    const number = extractNumber(chatItem);
    if (!number) return [];

    chatItem.click();
    await sleep(1000);

    const messages = getVisibleMessages();
    const leads = [];

    for (const msgEl of messages) {
      const text = getMessageText(msgEl);
      if (!text) continue;

      const lowerText = text.toLowerCase();

      for (const kw of keywords) {
        if (lowerText.includes(kw.keyword.toLowerCase())) {
          leads.push({
            number,
            numberNormalized: normalizeNumber(number),
            campaign: kw.campaign,
            keyword: kw.keyword,
            date: new Date().toISOString(),
            messageSnippet: text.substring(0, 120)
          });
          break;
        }
      }
    }

    return leads;
  }

  async function scanAllChats(keywords) {
    log('Starting scan...');
    const chatItems = getAllChatItems();

    if (chatItems.length === 0) {
      log('No chat items found on page');
      log('Page URL: ' + location.href);
      log('Document body children: ' + document.body.children.length);

      const debugInfo = {
        url: location.href,
        hasApp: !!document.querySelector('#app'),
        hasSide: !!document.querySelector('#side'),
        roleLists: document.querySelectorAll('div[role="list"]').length,
        roleListItems: document.querySelectorAll('div[role="listitem"]').length,
        allSpanTitles: document.querySelectorAll('span[title]').length
      };
      log('Debug info: ' + JSON.stringify(debugInfo));

      return {
        success: false,
        error: 'No se encontraron chats. Verificá que WhatsApp Web esté completamente cargado.',
        debug: debugInfo
      };
    }

    const allLeads = [];
    const processedNumbers = new Set();
    const maxChats = Math.min(chatItems.length, 50);

    log(`Processing ${maxChats} chats...`);

    for (let i = 0; i < maxChats; i++) {
      const chatItem = chatItems[i];
      const number = extractNumber(chatItem);

      if (!number) {
        log(`Chat ${i}: no phone number found, skipping`);
        continue;
      }

      const normalized = normalizeNumber(number);
      if (processedNumbers.has(normalized)) {
        log(`Chat ${i}: duplicate ${number}, skipping`);
        continue;
      }
      processedNumbers.add(normalized);

      log(`Chat ${i}: scanning ${number}...`);

      try {
        const leads = await scanSingleChat(chatItem, keywords);
        for (const lead of leads) {
          if (!allLeads.some(l =>
            l.numberNormalized === lead.numberNormalized &&
            l.campaign === lead.campaign
          )) {
            allLeads.push(lead);
            log(`  -> LEAD: ${lead.number} [${lead.keyword}]`);
          }
        }
      } catch (err) {
        log(`Error scanning chat ${number}: ${err.message}`);
      }
    }

    log(`Scan complete. Found ${allLeads.length} leads.`);
    return { success: true, leads: allLeads };
  }

  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'scanChats') {
      chrome.storage.sync.get(['keywords'], async (data) => {
        const keywords = data.keywords || [];
        if (keywords.length === 0) {
          sendResponse({ success: false, error: 'No hay palabras clave configuradas' });
          return;
        }

        try {
          const result = await scanAllChats(keywords);
          sendResponse(result);
        } catch (err) {
          sendResponse({ success: false, error: 'Error al escanear: ' + err.message });
        }
      });
      return true;
    }
  });

  log('Content script loaded on: ' + location.href);
})();
