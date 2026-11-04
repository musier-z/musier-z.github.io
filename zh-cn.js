/* Simplified Chinese localization. Text nodes are updated in place so React's
   event handlers, keyed lists, charts and MapLibre maps remain intact. */
(() => {
  'use strict';
  const nativeFetch = window.fetch.bind(window);
  const dictionary = Object.create(null);
  const pending = new Set();
  const attempts = new Map();
  const applied = new WeakMap();
  const originals = new WeakMap();
  const attributes = ['title', 'aria-label', 'placeholder', 'alt'];
  const ignore = /^(?:Tesla|Waymo|Zoox|Avride|Cybercab|Cybercabs|Model [YSX3]|VIN|VINs|ADS|AV|ODD|NHTSA|CPUC|TxDMV|DMV|FSD|R1|RT|I-PACE|Zeekr|ZEEKR|App Store|Google Play|OpenFreeMap|OpenMapTiles|OpenStreetMap|MapLibre|Autolane|autolane|Ethan McKanna|TX|CA|AZ|FL|GA|NV|TN|CO|DC|NY|SF|LA|US|USA|UK|X|CSV|JSON|PDF|API|URL|UTC|GMT|ID|AUS|SFO|PHX|LAX|CES|LiDAR|N\/A|—|–|[+-]?\d[\d,.%KMBkmb+\s/–−:$°]*|\w+@\w+\.\w+)$/;
  const cities = {
    'Bay Area':'旧金山湾区','Austin':'奥斯汀','Dallas':'达拉斯','Houston':'休斯敦','Tampa':'坦帕','Fort Worth':'沃思堡','Orlando':'奥兰多','Miami':'迈阿密','Phoenix':'凤凰城','Los Angeles':'洛杉矶','Las Vegas':'拉斯维加斯','San Diego':'圣迭戈','Atlanta':'亚特兰大','Nashville':'纳什维尔','San Antonio':'圣安东尼奥','Denver':'丹佛','San Francisco':'旧金山','London':'伦敦','Tokyo':'东京','Munich':'慕尼黑','New York':'纽约','Washington DC':'华盛顿特区','Seattle':'西雅图','Chicago':'芝加哥','Boston':'波士顿','Baltimore':'巴尔的摩','Charlotte':'夏洛特','Detroit':'底特律','Minneapolis':'明尼阿波利斯','New Orleans':'新奥尔良','Philadelphia':'费城','Pittsburgh':'匹兹堡','Portland':'波特兰','Sacramento':'萨克拉门托','St. Louis':'圣路易斯','Texas':'得克萨斯州','California':'加利福尼亚州','Arizona':'亚利桑那州','Florida':'佛罗里达州','Georgia':'佐治亚州','Tennessee':'田纳西州','Nevada':'内华达州','Colorado':'科罗拉多州','Lehi':'利希'
  };
  Object.assign(dictionary, cities, {
    'Robotaxi':'无人驾驶出租车','Tracker':'追踪','RobotaxiTracker':'无人驾驶出租车追踪','Robotaxi Tracker':'无人驾驶出租车追踪',
    'Dashboard':'总览','Vehicles':'车辆','Map':'地图','Cameras':'摄像头','Government':'政府数据','Robotaxi Weekly':'无人驾驶周报','Submit':'提交记录','Sign in':'登录','Sign up':'注册','Home':'首页','More':'更多','News':'新闻','Cities':'城市','Compare':'对比','About':'关于','Methodology':'统计方法','Privacy':'隐私政策','Terms':'使用条款',
    'All':'全部','All time':'全部时间','All cities':'全部城市','All providers':'全部运营商','All operators':'全部运营商','All 8 cities':'全部 8 个城市','Search':'搜索','Search vehicles…':'搜索车辆…','Search vehicles...':'搜索车辆…','Clear':'清除','Reset':'重置','Apply':'应用','Cancel':'取消','Close':'关闭','Back':'返回','Next':'下一页','Previous':'上一页','Loading…':'正在加载…','Loading...':'正在加载…','Retry':'重试','Refresh':'刷新','No results':'没有匹配结果','No results found':'没有找到匹配结果',
    'Tesla':'特斯拉','Tesla fleet':'特斯拉车队','Waymo fleet':'Waymo 车队','Zoox fleet':'Zoox 车队','Avride fleet':'Avride 车队','fleet':'车队','in':'位于','In service · unsupervised':'运营中 · 无安全员','In service':'运营中','Driverless':'全无人','Unsupervised':'无安全员','Supervised':'有安全员','Testing':'测试中','Test':'测试','Unclassified':'未分类','Live':'实时','Experimental':'实验性功能','Trips logged':'已记录行程','Cybercabs':'Cybercab 无人出租车','Cybercabs on camera · 24h':'摄像头发现 Cybercab · 24 小时','spotted':'已发现','lookup':'官方查询','spotted in Austin':'在奥斯汀发现','on Tesla\'s lookup':'特斯拉官方查询收录','registered in Texas':'在得克萨斯州注册','No safety driver':'无安全员','SPONSORED BY':'赞助商','Sponsored by':'赞助商','The Autonomous Delivery Platform':'自动驾驶配送平台',
    'Coverage in Austin':'奥斯汀服务覆盖','Travis & Williamson counties':'特拉维斯县和威廉森县','Expand':'展开地图','Area':'面积','Residents':'居民','Jobs':'就业岗位','Show Waymo':'显示 Waymo','Hide Waymo':'隐藏 Waymo','Service area':'服务区域','Cars per sq mi':'每平方英里车辆数','Residents per car':'每辆车对应居民数','AUS airport':'奥斯汀机场','Not served':'未覆盖','Also in Austin':'同样在奥斯汀运营','Tesla fares · Austin':'特斯拉车费 · 奥斯汀','Pricing →':'价格详情 →','Per mile':'每英里','Avg trip':'平均行程','Rides':'行程','WHERE FARES FALL':'车费分布','Where fares fall':'车费分布','MEDIAN FARE BY MONTH':'每月车费中位数','Median fare by month':'每月车费中位数','median ride · last 90 days':'单程中位数 · 近 90 天',
    'Fleet growth · Tesla · Austin':'车队增长 · 特斯拉 · 奥斯汀','Fleet growth':'车队增长','Driverless miles':'全无人行驶里程','Driverless miles per week':'每周全无人行驶里程','By platform':'按车型','Total':'合计','Platform':'车型','Miles':'英里','New cars':'新增车辆','3M':'近 3 个月','90d':'90 天','30d':'30 天','7d':'7 天','Hover, or focus and use ← →, to read any day':'悬停查看，或聚焦后用 ← → 读取任意日期','Tesla Robotaxi miles · no safety monitor':'特斯拉无人出租车里程 · 无安全员','Compare operators →':'对比运营商 →','Tesla safety report ↗':'特斯拉安全报告 ↗','· Tesla safety report ↗':'· 特斯拉安全报告 ↗','Stacked':'堆叠','By city':'按城市','Per week':'每周','Camera watch':'摄像头监测','In frame · 30 min':'画面内 · 近 30 分钟','Seen · 24 h':'发现次数 · 24 小时','Per 1,000 vehicles':'每千辆车检出次数','Cameras · 30 min':'摄像头 · 近 30 分钟','By hour · past 24 h':'按小时 · 过去 24 小时','Latest sightings':'最新目击记录','See every sighting live →':'查看全部实时记录 →','About these numbers':'这些数据如何计算','Hourly trends & stats →':'小时趋势与统计 →','View cameras on map →':'在地图上查看摄像头 →','now':'当前','today':'今天','vehicles':'车辆','snapshots':'快照','downtime':'离线时段','· by day':'· 按天',
    'Full report →':'完整报告 →','Mostly positive':'以正面为主','Mixed':'褒贬不一','Net sentiment':'净情绪值','negative':'负面','neutral':'中性','positive':'正面','Top theme':'热门话题','An automated daily read of posts on X, not an official measure of public opinion.':'每日自动分析 X 平台帖文，不属于官方民意调查。','US robotaxi fleet · driverless':'美国无人出租车队 · 全无人','By operator and state →':'按运营商与州查看 →','stated':'官方公布','WHERE THEY RUN':'运营分布','Where they run':'运营分布','Sources and evidence':'来源与证据','Texas DMV registrations · Tesla':'得州 DMV 注册记录 · 特斯拉','Every VIN →':'查看全部 VIN →','Registered AV fleet':'已注册自动驾驶车队','Last 30 days':'过去 30 天','Matched to tracked plates':'已匹配追踪车牌','Cybercab':'Cybercab','Model Y':'Model Y','Cities · 16 live markets':'城市 · 16 个运营市场','All 34 cities →':'查看全部 34 个城市 →','Live · sized by cars tracked':'运营中 · 圆点大小代表追踪车辆数','Waitlist':'候补名单','Testing or announced':'测试中或已宣布','Abroad:':'海外：','LIVE MARKETS':'运营市场','CARS TRACKED':'已追踪车辆','Robotaxi news':'无人驾驶出租车新闻','All stories →':'全部新闻 →','Subscribe →':'订阅 →','Tesla crash reports · NHTSA':'特斯拉事故报告 · NHTSA','Full records →':'完整记录 →','crash reports filed':'已提交事故报告','last 90 days':'近 90 天','ADS engaged':'ADS 已启用','not engaged':'未启用','WHERE':'地点','WHO WAS AT FAULT':'责任分析','other party at fault':'其他方责任','unclear':'不明确','MOST COMMON WHEN TESLA WAS AT FAULT':'特斯拉责任时的常见情形','MOST COMMON WHEN THE OTHER PARTY WAS':'其他方责任时的常见情形','HOW SEVERE':'严重程度','No injuries':'无人员受伤','Property damage':'财产损失','Minor injury':'轻伤','Serious or fatal':'重伤或死亡','COLLIDED WITH':'碰撞对象','Other Fixed Object':'其他固定物体','SUV':'SUV','Cyclist':'骑行者','Passenger Car':'乘用车','ROAD':'道路类型','Street':'街道','Intersection':'交叉路口','Parking Lot':'停车场','Highway / Freeway':'高速公路','WEATHER':'天气','Clear':'晴朗','Partly Cloudy':'局部多云','Cloudy':'多云','AFTERWARDS':'事故后情况','A vehicle was towed':'有车辆被拖走','Inside its design domain':'处于设计运行范围内','NEWEST REPORTS':'最新报告',
    'Robotaxi Tracker for iPhone and Android':'无人驾驶出租车追踪 · iPhone 与安卓应用','Free. Sync your rides, get a weekly recap, and share what you spot.':'免费使用。同步行程、查看每周回顾，并分享您的发现。','Download on the':'下载于','Get it on':'下载于','US fleet':'美国车队','Robotaxi miles':'无人驾驶里程','Just spotted':'最新发现','X sentiment':'X 平台舆情','Government data':'政府数据','Wait times':'等车时间','Pricing':'价格','Leaderboards':'排行榜','A project by':'原站作者：',
    'This project is an independent platform and is not affiliated with, authorized by, endorsed by, or in any way officially connected with Tesla, Inc., Waymo LLC, Alphabet Inc., Zoox, Inc., Amazon.com, Inc., Avride, or any of their subsidiaries or affiliates.':'本项目是独立平台，与 Tesla、Waymo、Alphabet、Zoox、Amazon、Avride 及其子公司或关联方不存在隶属、授权、背书或其他官方关联。',
    'Provider names and related marks, emblems, and images are trademarks of their respective owners. All trademarks referenced herein are the property of their respective owners and are used for identification purposes only.':'运营商名称及相关标识、徽标和图像均属于其各自权利人。此处引用的商标仅用于识别相应主体。'
  });
  Object.assign(dictionary, window.__ZH_GLOSSARY || {});
  const casefoldGlossary = Object.fromEntries(Object.entries(window.__ZH_GLOSSARY || {}).filter(([key])=>key.length>10).map(([key,value])=>[key.toLowerCase(),value]));
  const sourceEntries = Object.entries(cities).sort((a,b)=>b[0].length-a[0].length);
  let timer, walking = false, processing = false;
  let ready = false;
  const skipped = node => !node.parentElement || !!node.parentElement.closest('script,style,textarea,input,code,pre,[data-no-translate],.zh-original-dialog,a[href^="/u/"]');
  function normalize(s) { return s.replace(/\s+/g, ' ').trim(); }
  function needs(s) { return /[A-Za-z]{2}/.test(s) && !ignore.test(s) && !/^https?:|^www\.|^@|^[\w.-]+@[\w.-]+\./.test(s) && !/^[A-Z0-9-]{5,20}$/.test(s); }
  function lookup(s) {
    if (/^@|^https?:|^[\w.-]+@[\w.-]+\.|^[\w.-]+\.(?:com|org|net|io|co|gov|edu|toyota)$/.test(s)) return s;
    if (/^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{1,2}$/.test(s)) {const [m,d]=s.split(' ');return {Jan:1,Feb:2,Mar:3,Apr:4,May:5,Jun:6,Jul:7,Aug:8,Sep:9,Oct:10,Nov:11,Dec:12}[m]+'月'+d+'日';}
    if (window.__ZH_GLOSSARY?.[s] !== undefined) return window.__ZH_GLOSSARY[s];
    if (casefoldGlossary[s.toLowerCase()] !== undefined) return casefoldGlossary[s.toLowerCase()];
    if (/^\d[\d,.KMBkmb]*\s*mi[²2]?$/.test(s)) return s.replace(/mi[²2]/,'平方英里').replace(/mi/,'英里');
    if (/^\d{1,2}:\d{2}\s*(AM|PM)$/.test(s)) return s.replace(/(\d{1,2}):(\d{2})\s*(AM|PM)/,(_,h,m,p)=>String(Number(h)%12+(p==='PM'?12:0)).padStart(2,'0')+':'+m);
    if (/^\d[\d,.]*\s*TX$/.test(s)) return s.replace(/TX$/,'得州');
    if (dictionary[s] !== undefined) return dictionary[s];
    if (!needs(s)) return s;
    let t = s;
    for (const [en,zh] of sourceEntries) t = t.replace(new RegExp('\\b'+en.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'\\b','g'),zh);
    t = t.replace(/\bTesla\b/g,'特斯拉');
    t = t.replace(/\b(\d[\d,.]*)\s*sq mi\b/g,'$1 平方英里').replace(/\bsq mi\b/g,'平方英里');
    t = t.replace(/^([\d,.]+)\+? cars$/,'$1+ 辆').replace(/^(\d+)m ago$/,'$1 分钟前').replace(/^(\d+)h ago$/,'$1 小时前').replace(/^(\d+)d ago$/,'$1 天前');
    t = t.replace(/\bin (\d+)d\b/g,'近 $1 天').replace(/\bin (\d+) days\b/g,'近 $1 天').replace(/\bin (\d+) cars\b/g,'来自 $1 辆车').replace(/\bof the fleet\b/g,'占车队比例').replace(/\bof metro\b/g,'占都会区比例');
    t = t.replace(/\b(\d[\d,.]*) posts reviewed\b/g,'已分析 $1 条帖文').replace(/\b(\d[\d,.]*)% driverless\b/g,'$1% 为全无人车辆');
    t = t.replace(/\b(\d+) in frame now\b/g,'当前画面内 $1 辆').replace(/\bChecked (\d+)m ago\b/g,'$1 分钟前检查').replace(/\blast sighting (\d+)m ago\b/g,'最近一次发现于 $1 分钟前');
    t = t.replace(/\bmedian ride · last (\d+) days\b/g,'单程中位数 · 近 $1 天');
    const monthNumber = {Jan:1,Feb:2,Mar:3,Apr:4,May:5,Jun:6,Jul:7,Aug:8,Sep:9,Oct:10,Nov:11,Dec:12};
    t = t.replace(/\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (\d{1,2}), (\d{4})\b/g,(_,m,d,y)=>y+'年'+monthNumber[m]+'月'+d+'日');
    t = t.replace(/^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*[’'](\d{2})$/,(_,m,y)=>'20'+y+'年'+monthNumber[m]+'月');
    t = t.replace(/^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (\d{1,2})$/,(_,m,d)=>monthNumber[m]+'月'+d+'日');
    t = t.replace(/^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)$/,m=>monthNumber[m]+'月');
    if (!/[a-z]{2}/i.test(t.replace(/Cybercab|Waymo|Zoox|Avride|Model Y|VIN|ADS|NHTSA|CPUC|DMV|TX|CA|FL|AZ|K|M|B/g,''))) return t;
    if (!pending.has(s) && (attempts.get(s)||0)<3) {pending.add(s); scheduleTranslation();}
    return t;
  }
  function updateText(node) {
    if (skipped(node) || !node.nodeValue?.trim()) return;
    const previous = applied.get(node);
    const original = previous === node.nodeValue ? originals.get(node) : node.nodeValue;
    if (!original) return;
    originals.set(node, original);
    const trimmed = normalize(original);
    let translated = lookup(trimmed);
    if (/^(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{2}$/.test(trimmed) && node.parentElement.closest('svg')) {
      // A month plus two digits is ambiguous (day vs. year). Fleet history
      // uses years; camera history uses days. Read the surrounding card.
      let context = node.parentElement.closest('svg').parentElement;
      for(let i=0;i<5 && context && !context.querySelector('a[href="/fleet"]');i++)context=context.parentElement;
      if(context?.querySelector('a[href="/fleet"]') && context!==document.body && context.tagName!=='MAIN') {
        const [month,year]=trimmed.split(' ');translated='20'+year+'年'+({Jan:1,Feb:2,Mar:3,Apr:4,May:5,Jun:6,Jul:7,Aug:8,Sep:9,Oct:10,Nov:11,Dec:12}[month])+'月';
      }
    }
    if (trimmed === 'in') {
      const context = node.parentElement.textContent;
      translated = node.parentElement.closest('h1') ? '位于' : /cars|辆车|汽车/.test(context) ? '来自' : /\d+d|\d+\s*days|\d+\s*天/.test(context) ? '近' : '于';
    }
    if (trimmed === 'Area' && location.pathname.startsWith('/vehicles')) translated = '地区';
    if (trimmed === 'By') translated = '按';
    const value = original.replace(original.trim(), translated);
    if (node.nodeValue !== value) node.nodeValue = value;
    applied.set(node, value);
  }
  function walk(root = document.body) {
    if (!root || walking) return;
    walking = true;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) updateText(walker.currentNode);
    for (const element of root.querySelectorAll('[title],[aria-label],[placeholder],img[alt]')) {
      if (element.closest('[data-no-translate]')) continue;
      for (const attribute of attributes) {
        const value = element.getAttribute(attribute);
        if (value && needs(value) && !/[\u4e00-\u9fff]/.test(value)) {
          const translated = lookup(value);
          if (translated !== value) element.setAttribute(attribute, translated);
        }
      }
    }
    document.documentElement.lang = 'zh-CN';
    const titles = {'/':'车队数据与服务地图','/vehicles':'车辆目录','/map':'服务区域地图','/cameras':'交通摄像头监测','/government':'政府公开数据','/government/crashes':'事故报告','/government/incidents':'城市事件','/government/austin':'奥斯汀事件记录','/government/cpuc':'加州运营数据','/government/citations':'旧金山停车罚单','/permits':'运营许可与注册记录','/permits/california':'加州运营许可','/permits/arizona':'亚利桑那州注册记录','/permits/texas':'得州注册记录','/fleet':'美国全无人车队','/miles':'全无人行驶里程','/spotted':'最新目击记录','/sentiment':'X 平台舆情','/cities':'运营城市','/compare':'运营商对比','/cybercab':'Cybercab 无人出租车','/cybercab-event':'Cybercab 活动','/leaderboards':'贡献排行榜','/pricing':'乘车价格','/wait-times':'等车时间','/stats':'运营统计','/news':'行业新闻','/about':'关于本站','/methodology':'统计方法','/privacy':'隐私政策','/terms':'使用条款','/signin':'登录','/signup':'注册','/submit':'提交记录'};
    const pageTitle = titles[location.pathname] || (location.pathname.startsWith('/vehicles/')?'车辆 '+decodeURIComponent(location.pathname.split('/').pop()):location.pathname.startsWith('/cities/')?'城市详情':location.pathname.startsWith('/compare/')?'运营商对比':'无人驾驶数据');
    const title = pageTitle+' | 无人驾驶出租车追踪';
    if (document.title !== title) document.title = title;
    decorate();
    walking = false;
  }
  function scheduleTranslation() { if (!timer) timer = setTimeout(flush, 150); }
  async function flush() {
    timer = null;
    if (processing || !pending.size) return;
    processing = true;
    const texts = [...pending].slice(0,120);
    for(const s of texts) {pending.delete(s);attempts.set(s,(attempts.get(s)||0)+1);}
    try {
      const translated = await translatePublicText(texts);
      Object.assign(dictionary, translated);
      if(Object.keys(translated).length) await nativeFetch('/__local/translation-cache', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(translated)});
    } catch (_) { /* Retain readable source data if the optional translator is offline. */ }
    processing = false;
    walk();
    if(pending.size) scheduleTranslation();
  }
  async function translatePublicText(texts) {
    const result = {}, groups = []; let group = [], length = 0;
    for(const text of texts) {if(length+text.length>2200&&group.length){groups.push(group);group=[];length=0;}group.push(text);length+=text.length+12;}
    if(group.length)groups.push(group);
    for(const batch of groups) {
      const q=batch.map((text,i)=>'['+i+'] '+text).join('\n');
      const parameters=new URLSearchParams({client:'gtx',sl:'en',tl:'zh-CN',dt:'t',q});
      const response=await nativeFetch('https://translate.googleapis.com/translate_a/single?'+parameters, {signal:AbortSignal.timeout(15000)});
      if(!response.ok)throw new Error('Translation unavailable');
      const payload=await response.json();const output=payload[0].map(row=>row[0]||'').join('');
      const parts=output.split(/\[\s*(\d+)\s*\]\s*/);
      for(let i=1;i<parts.length-1;i+=2){const index=Number(parts[i]);if(index<batch.length)result[batch[index]]=polish(parts[i+1].trim());}
      if(batch.length===1&&!result[batch[0]])result[batch[0]]=polish(output.replace(/^\[0\]\s*/,'').trim());
    }
    return result;
  }
  function polish(text) {
    return text.replace(/机队/g,'车队').replace(/机器人出租车|机器人轴/g,'无人驾驶出租车').replace(/无人监督|无人监管|完全不受监管|没有安全监视器|没有安全驾驶员/g,'无安全员').replace(/安全监视器|安全监控员/g,'安全员').replace(/里程数/g,'里程').replace(/韦莫|维莫/g,'Waymo').replace(/佐克斯/g,'Zoox').replace(/阿夫莱德/g,'Avride').replace(/赛博出租车/g,'Cybercab').replace(/德克萨斯/g,'得克萨斯').replace(/沃斯堡/g,'沃思堡').replace(/休斯顿/g,'休斯敦').replace(/圣地亚哥/g,'圣迭戈').replace(/崩溃报告/g,'事故报告').replace(/加州游乐设施/g,'加州行程').replace(/顺丰停车票/g,'旧金山停车罚单').replace(/游乐设施/g,'乘车服务').replace(/骑手/g,'乘客').replace(/民意调查(?= \d|开始|于)/g,'查询').replace(/Robotaxi Tracker|无人驾驶出租车追踪器/g,'无人驾驶出租车追踪');
  }
  function decorate() {
    const brand = document.querySelector('header a[href="/"]');
    if (brand && !brand.querySelector('.zh-source-badge')) {
      const badge = document.createElement('span');
      badge.className='zh-source-badge';badge.textContent='中文版';badge.setAttribute('data-no-translate','');brand.appendChild(badge);
    }
    const footer = document.querySelector('footer > div');
    if (footer && !footer.querySelector('.zh-source')) {
      const credit = document.createElement('div');credit.className='zh-source';credit.setAttribute('data-no-translate','');
      credit.innerHTML='简体中文镜像 · 原站内容与数据：<a href="https://robotaxitracker.com/" target="_blank" rel="noopener noreferrer">Robotaxi Tracker</a> · 保留原始统计口径与来源；缓存时间不代表数据统计日期。<br>账户登录与投稿请前往原站。本站使用人工术语表与机器翻译，专有名称、车牌、VIN 和引用链接保留原文。';
      footer.appendChild(credit);
    }
    if (document.querySelector('main') && !ready) {
      ready = true;
      setTimeout(()=>document.getElementById('zh-loading')?.remove(),120);
    }
  }
  function originalDialog(path) {
    if(document.querySelector('.zh-original-dialog')) return;
    const lastFocused = document.activeElement;
    const overlay=document.createElement('div');overlay.className='zh-original-dialog';
    overlay.innerHTML='<section role="dialog" aria-modal="true" aria-labelledby="zh-dialog-title"><h2 id="zh-dialog-title">前往原站使用账户功能</h2><p>这是 Robotaxi Tracker 的简体中文镜像。登录、注册与提交记录由原站处理，您的账户信息不会在此镜像中收集。</p><a target="_blank" rel="noopener noreferrer">前往原站</a><button type="button">继续浏览</button></section>';
    overlay.querySelector('a').href='https://robotaxitracker.com'+path;
    const close=()=>{overlay.remove();lastFocused?.focus();};
    overlay.querySelector('button').onclick=close;
    overlay.onclick=e=>{if(e.target===overlay)close();};
    overlay.addEventListener('keydown',e=>{if(e.key==='Escape')close();if(e.key==='Tab'){const a=overlay.querySelector('a'),b=overlay.querySelector('button');if(e.shiftKey&&document.activeElement===a){e.preventDefault();b.focus();}else if(!e.shiftKey&&document.activeElement===b){e.preventDefault();a.focus();}}});
    document.body.appendChild(overlay);overlay.querySelector('a').focus();
  }
  document.addEventListener('click', e=>{
    const link=e.target.closest?.('a[href]');if(!link)return;
    const url=new URL(link.href,location.href);
    if(url.origin===location.origin && /^\/(signin|signup|submit|settings|delete-account|review)(\/|$)/.test(url.pathname)) {
      e.preventDefault();e.stopImmediatePropagation();originalDialog(url.pathname);
    }
  },true);
  // Original analytics, OAuth and writes are not connected to the mirror.
  window.fetch=(input,init)=>{
    const url=typeof input==='string'?input:input.url;
    if(/google-analytics\.com|plausible\.io|cloudflareinsights\.com/.test(url))return Promise.resolve(new Response(null,{status:204}));
    return nativeFetch(input,init);
  };
  const dictionaryReady = nativeFetch('/translations.json').then(r=>r.json()).then(data=>{for(const [k,v] of Object.entries(data))if(dictionary[k]===undefined)dictionary[k]=polish(v);}).catch(()=>{});
  async function start() {
    await dictionaryReady;
    const observer = new MutationObserver(records=>{
      if(walking)return;
      let children=false;
      for(const record of records){if(record.type==='characterData'){if(applied.get(record.target)!==record.target.nodeValue)updateText(record.target);}else children=true;}
      if(children){clearTimeout(window.__zhWalkTimer);window.__zhWalkTimer=setTimeout(walk,35);}
    });
    observer.observe(document.body,{subtree:true,childList:true,characterData:true});
    observer.observe(document.head,{subtree:true,childList:true,characterData:true});
    walk();
    setTimeout(()=>{if(!ready){const label=document.querySelector('#zh-loading span');if(label)label.textContent='正在连接公开数据服务，请稍候…';}},7000);
    setTimeout(()=>document.getElementById('zh-loading')?.remove(),20000);
    window.__zh={dictionary, pending, attempts, walk, originalDialog, translatePublicText, polish, audit:()=>{const result=[];const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);while(w.nextNode()){const n=w.currentNode;const text=normalize(n.nodeValue||'');if(!skipped(n)&&needs(text)&&!/[\u4e00-\u9fff]/.test(text)&&!dictionary[text])result.push(text);}return [...new Set(result)];}};
    if(/^\/(signin|signup|submit|settings|delete-account|review)(\/|$)/.test(location.pathname)) originalDialog(location.pathname);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
