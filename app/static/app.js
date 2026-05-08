
const API = {
  token: localStorage.getItem("sr_token") || "",
  user: null,
  async call(path, opts={}) {
    const headers = {"Content-Type":"application/json", ...(opts.headers||{})};
    if (this.token) headers.Authorization = "Bearer " + this.token;
    const res = await fetch(path, {...opts, headers});
    if (!res.ok) {
      let msg = "Villa kom upp.";
      try { msg = (await res.json()).detail || msg; } catch {}
      throw new Error(msg);
    }
    return res.json();
  }
};

const SUBJECTS = {
  mixed:{name:"Blandað Royale",icon:"🎯",xpBonus:1.25},
  math:{name:"Stærðfræði",icon:"🧮",xpBonus:1},
  icelandic:{name:"Íslenska",icon:"🇮🇸",xpBonus:1},
  english:{name:"Enska",icon:"🇬🇧",xpBonus:1},
  science:{name:"Náttúrufræði",icon:"🌿",xpBonus:1},
  geo:{name:"Landafræði",icon:"🌍",xpBonus:1}
};

let state = {
  level:1,xp:0,coins:0,streak:0,shields:0,hints:2,skips:2,loot_boxes:0,
  total_correct:0,total_answered:0,boss_wins:0,zone:"mixed",gradeLevel:"5",adaptiveMode:false,owned:{},pets:{},collectibles:{},activePet:null,achievements:{},current:null,
  bossMode:false,bossLeft:0,bossMax:5
};

let daily = JSON.parse(localStorage.getItem("sr_daily") || "null");
let dailyLogin = JSON.parse(localStorage.getItem("sr_daily_login") || "null");
let QUESTION_BANK = [];
let CUSTOM_QUESTION_BANK = [];
let PACK_QUESTION_BANK = [];
let ASSIGNED_PACKS = [];
let teacherQuestionsCache = [];
let missionPacksCache = [];
let MY_SKILL_STATS = [];
let LEARNING_PATHS = [];
let teacherLearningPathsCache = [];
let currentStudentDetailId = null;

const shopItems = [
  {id:"shield",icon:"🛡️",title:"Skjöldur",price:180,desc:"Bjargar streak ef svarið er rangt.",kind:"consumable",rarity:"common"},
  {id:"hint",icon:"💡",title:"Vísbending",price:120,desc:"Sýnir hjálp við verkefni.",kind:"consumable",rarity:"common"},
  {id:"skip",icon:"⏭️",title:"Mission skipti",price:100,desc:"Skiptu um verkefni án refsingar.",kind:"consumable",rarity:"common"},
  {id:"firststep",icon:"🔎",title:"Fyrsta skref",price:220,desc:"Sýnir fyrsta skrefið í krefjandi verkefni.",kind:"consumable",rarity:"rare"},
  {id:"remove2",icon:"🎯",title:"Fjarlægja 2 röng",price:260,desc:"Hjálpar í fjölvali með því að fjarlægja tvo ranga möguleika.",kind:"consumable",rarity:"rare"},
  {id:"loot",icon:"🎁",title:"Loot kassi",price:350,desc:"Tilviljunarkennd verðlaun og safngripir.",kind:"consumable",rarity:"rare"},
  {id:"focus",icon:"🧠",title:"Fókus-bónus",price:450,desc:"Gefur +150 XP strax.",kind:"boost",rarity:"rare"},
  {id:"double",icon:"⚡",title:"Rafmagns XP",price:650,desc:"Gefur +300 XP og confetti storm.",kind:"boost",rarity:"epic"},
  {id:"theme_space",icon:"🌌",title:"Geimstöð",price:900,desc:"Opnar geimþema.",kind:"theme",rarity:"epic"},
  {id:"theme_lava",icon:"🌋",title:"Eldfjallaeyja",price:900,desc:"Opnar eldþema.",kind:"theme",rarity:"epic"},
  {id:"theme_ice",icon:"🧊",title:"Ísheimur",price:900,desc:"Opnar ísþema.",kind:"theme",rarity:"epic"},
  {id:"crown",icon:"👑",title:"Kóróna",price:1200,desc:"Sýnir Legendary stemningu á prófílnum.",kind:"cosmetic",rarity:"legendary"},
  {id:"dragon",icon:"🐉",title:"Dreka-avatar",price:1500,desc:"Breytir avatar í dreka.",kind:"cosmetic",rarity:"legendary"},
  {id:"ninja",icon:"🥷",title:"Ninja-avatar",price:1000,desc:"Leyndarmál meistaranemans.",kind:"cosmetic",rarity:"epic"},
  {id:"pet_owl",icon:"🦉",title:"Ugla",price:800,desc:"Lukkudýr sem elskar vísbendingar.",kind:"pet",rarity:"rare"},
  {id:"pet_fox",icon:"🦊",title:"Refur",price:900,desc:"Snjallt lukkudýr fyrir orð og lausnir.",kind:"pet",rarity:"epic"},
  {id:"pet_robot",icon:"🤖",title:"Mini-botti",price:1000,desc:"Tækni-lukkudýr fyrir stærðfræði.",kind:"pet",rarity:"epic"},
  {id:"pet_penguin",icon:"🐧",title:"Mörgæs",price:700,desc:"Ískaldur fókusvinur.",kind:"pet",rarity:"rare"}
];

const collectibleItems = [
  {id:"pencil_gold", icon:"✏️", title:"Gullblýantur", rarity:"rare"},
  {id:"word_sword", icon:"🗡️", title:"Orðasverð", rarity:"epic"},
  {id:"science_orb", icon:"🔮", title:"Vísindakúla", rarity:"epic"},
  {id:"map_key", icon:"🗝️", title:"Kortalykill", rarity:"rare"},
  {id:"knowledge_stone", icon:"💎", title:"Þekkingarsteinn", rarity:"legendary"},
  {id:"royale_trophy", icon:"🏆", title:"Skóla-Royale bikar", rarity:"legendary"}
];

const subjectBosses = {
  math:{icon:"🧮",name:"Margföldunartröllið",reward:520},
  icelandic:{icon:"🇮🇸",name:"Orðflokksdrekinn",reward:520},
  english:{icon:"🇬🇧",name:"Grammar Goblin",reward:520},
  science:{icon:"🌿",name:"Vísindavargurinn",reward:520},
  geo:{icon:"🌍",name:"Kortakóngurinn",reward:520},
  mixed:{icon:"👑",name:"Dreki Þekkingarinnar",reward:650}
};

const achievementDefs = [
  {id:"first", icon:"🎯", title:"Fyrsta lending", desc:"Svaraðu einu verkefni rétt.", reward:80, check:()=>state.total_correct>=1},
  {id:"streak3", icon:"🔥", title:"3 í röð", desc:"Náðu þremur réttum í röð.", reward:120, check:()=>state.streak>=3},
  {id:"streak5", icon:"⚡", title:"5 í röð", desc:"Náðu fimm réttum í röð.", reward:180, check:()=>state.streak>=5},
  {id:"ten", icon:"🏅", title:"10 rétt", desc:"Svaraðu 10 verkefnum rétt.", reward:260, check:()=>state.total_correct>=10},
  {id:"level3", icon:"🚀", title:"Level 3", desc:"Komdu nemanda í level 3.", reward:250, check:()=>state.level>=3},
  {id:"level5", icon:"👑", title:"Level 5", desc:"Komdu nemanda í level 5.", reward:500, check:()=>state.level>=5}
];

const dailyOptions = [
  {id:"correct5", text:"Náðu 5 réttum svörum.", target:5, reward:220},
  {id:"streak3", text:"Náðu 3 réttum í röð.", target:3, reward:180},
  {id:"answer10", text:"Svaraðu 10 verkefnum.", target:10, reward:240}
];

function rand(min,max){return Math.floor(Math.random()*(max-min+1))+min}
function pick(a){return a[Math.floor(Math.random()*a.length)]}
function shuffle(a){return [...a].sort(()=>Math.random()-0.5)}
function normalize(v){return String(v).trim().toLowerCase().replace(",",".")}
function xpNeeded(){return 100+(state.level-1)*35}
function q(subject,text,answer,hint,options=null){
  let opts = options;
  if(!opts && !Number.isNaN(Number(answer))){
    const n=Number(answer), wrong=new Set();
    while(wrong.size<3){let w=n+rand(-12,12); if(w!==n && w>=0) wrong.add(String(w))}
    opts=[String(answer),...wrong];
  }
  return {subject,text,answer:String(answer),hint,options:opts?shuffle(opts.map(String)):null, grade_level: effectiveGradeLevel(), difficulty: Math.max(1, effectiveGradeLevel()-4)};
}

/* ---------- verkefnagenerering ---------- */
function makeMathQuestion(){
  const t=pick(["add","sub","mult","div","clock","money","area","perimeter","rounding","missing","sequence","fraction","unit","compare","word"]);
  if(t==="add"){let a=rand(12,499),b=rand(8,380);return q("math",`Hvað er ${a} + ${b}?`,a+b,"Leggðu saman hundruð, tugi og einingar.")}
  if(t==="sub"){let a=rand(80,550),b=rand(10,Math.min(240,a-5));return q("math",`Hvað er ${a} - ${b}?`,a-b,"Dragðu fyrst frá hundruð/tugi og svo einingar.")}
  if(t==="mult"){let a=rand(2,12),b=rand(2,12);return q("math",`Hvað er ${a} × ${b}?`,a*b,"Margföldun er endurtekin samlagning.")}
  if(t==="div"){let b=rand(2,12),ans=rand(2,12),a=b*ans;return q("math",`Hvað er ${a} : ${b}?`,ans,`Hvaða tala sinnum ${b} gefur ${a}?`)}
  if(t==="clock"){let h=rand(1,10),add=rand(1,8),ans=((h+add-1)%12)+1;return q("math",`Klukkan er ${h}:00. Hvað verður hún eftir ${add} klst.?`,ans,"Bættu við klukkutímunum.")}
  if(t==="money"){let price=rand(120,2490),paid=Math.ceil((price+rand(50,700))/100)*100;return q("math",`Hlutur kostar ${price} kr. Þú borgar ${paid} kr. Hvað færðu til baka?`,paid-price,"Til baka = borgað - verð.")}
  if(t==="area"){let l=rand(3,15),w=rand(2,12);return q("math",`Rétthyrningur er ${l} cm × ${w} cm. Hvert er flatarmálið?`,l*w,"Flatarmál = lengd × breidd.")}
  if(t==="perimeter"){let l=rand(3,15),w=rand(2,12);return q("math",`Rétthyrningur er ${l} cm á lengd og ${w} cm á breidd. Hvert er ummálið?`,2*l+2*w,"Ummál = allar hliðar lagðar saman.")}
  if(t==="rounding"){let n=rand(21,999);return q("math",`Námundaðu ${n} að næsta tug.`,Math.round(n/10)*10,"Eining 5 eða meira fer upp.")}
  if(t==="sequence"){let start=rand(2,30),step=rand(2,12);return q("math",`Hvaða tala kemur næst: ${start}, ${start+step}, ${start+step*2}, ___?`,start+step*3,"Finndu hvað bætist við í hvert skipti.")}
  if(t==="fraction"){let whole=pick([20,30,40,50,60,80,100,120,200]);return q("math",`Hvað er helmingurinn af ${whole}?`,whole/2,"Helmingur þýðir að skipta í tvo jafna hluta.")}
  if(t==="unit"){let m=rand(2,12);return pick([
    q("math",`Hvað eru ${m} metrar margir sentímetrar?`,m*100,"1 metri = 100 sentímetrar."),
    q("math",`Hvað eru ${m} lítrar margir millilítrar?`,m*1000,"1 lítri = 1000 millilítrar."),
    q("math",`Hvað eru ${m} kílómetrar margir metrar?`,m*1000,"1 kílómetri = 1000 metrar.")
  ])}
  if(t==="compare"){let a=rand(2,12),b=rand(2,12),c=rand(2,12),d=rand(2,12);return q("math",`Hvort er stærra? ${a}×${b} eða ${c}×${d}. Skrifaðu stærri útkomuna.`,Math.max(a*b,c*d),"Reiknaðu bæði dæmin og berðu saman.")}
  if(t==="word"){let kids=rand(3,9),each=rand(4,14);return q("math",`${kids} nemendur fá ${each} límmiða hver. Hvað eru það margir límmiðar samtals?`,kids*each,"Margfaldaðu fjölda nemenda með límmiðum.")}
  let x=rand(4,28),ans=rand(3,30),sum=x+ans;return q("math",`Hvaða tala vantar? ${x} + __ = ${sum}`,ans,`Finndu hvað vantar upp á ${sum}.`);
}

function makeIcelandicQuestion(){
  const sentences=[
    {s:"Strákurinn hleypur hratt.",verb:"hleypur",noun:"Strákurinn",adj:"hratt"},
    {s:"Kötturinn sefur lengi.",verb:"sefur",noun:"Kötturinn",adj:"lengi"},
    {s:"Stelpan les góða bók.",verb:"les",noun:"Stelpan",adj:"góða"},
    {s:"Hundurinn geltir hátt.",verb:"geltir",noun:"Hundurinn",adj:"hátt"},
    {s:"Barnið teiknar stórt hús.",verb:"teiknar",noun:"Barnið",adj:"stórt"}
  ];
  const words=[
    ["glaður","leiður","kátur"],["stór","lítill","mikill"],["fljótur","hægur","snöggur"],["kaldur","heitur","svalur"],
    ["fallegur","ljótur","fagur"],["sterkur","veikur","öflugur"],["bjartur","dimmmur","ljós"]
  ];
  const spelling=[
    ["skóli",["skoli","skólli","sgóli"]],["hestur",["hesttir","hestyr","hesturr"]],["vinur",["vinnur","vinyr","vynur"]],
    ["fjall",["fjal","fjahl","fjalll"]],["köttur",["kötur","kötturr","kottur"]],["sólskin",["sólskinnn","solskin","sólsgin"]]
  ];
  const plurals=[["hestur","hestar"],["bók","bækur"],["stelpa","stelpur"],["bíll","bílar"],["köttur","kettir"],["barn","börn"],["maður","menn"],["fjall","fjöll"]];
  const t=pick(["verb","noun","adj","opposite","synonym","spelling","plural","category","capital","sentence"]);
  if(t==="verb"){let s=pick(sentences); return q("icelandic",`Finndu sagnorðið: „${s.s}“`,s.verb,"Sagnorð er eitthvað sem einhver gerir.",[s.verb,s.noun,s.adj,"og"])}
  if(t==="noun"){let s=pick(sentences); return q("icelandic",`Finndu nafnorðið: „${s.s}“`,s.noun,"Nafnorð er heiti á manneskju, dýri, hlut eða stað.",[s.noun,s.verb,s.adj,"vel"])}
  if(t==="adj"){let s=pick(sentences); return q("icelandic",`Hvaða orð lýsir einhverju? „${s.s}“`,s.adj,"Lýsingarorð lýsir hvernig eitthvað er.",[s.adj,s.verb,s.noun,"og"])}
  if(t==="opposite"){let [w,opp,syn]=pick(words); return q("icelandic",`Hvað er andheiti við „${w}“?`,opp,"Andheiti er gagnstæð merking.",[opp,syn,w,"borð"])}
  if(t==="synonym"){let [w,opp,syn]=pick(words); return q("icelandic",`Hvað er samheiti við „${w}“?`,syn,"Samheiti er orð með svipaða merkingu.",[syn,opp,w,"skóli"])}
  if(t==="spelling"){let [a,w]=pick(spelling); return q("icelandic","Veldu rétt skrifað orð.",a,"Horfðu vel á stafina.",[a,...w])}
  if(t==="plural"){let [sing,pl]=pick(plurals); return q("icelandic",`Hvað er fleirtala af „${sing}“?`,pl,"Fleirtala merkir fleiri en einn.",[pl,sing+"ir",sing+"ar",sing+"ur"])}
  if(t==="category"){return pick([
    q("icelandic","Hvaða orð er nafnorð?","bolti","Nafnorð er heiti á hlut, dýri, manneskju eða stað.",["bolti","hlaupa","fallegur","hratt"]),
    q("icelandic","Hvaða orð er sagnorð?","syngja","Sagnorð er eitthvað sem einhver gerir.",["syngja","skóli","rauður","lítill"]),
    q("icelandic","Hvaða orð er lýsingarorð?","gulur","Lýsingarorð lýsir nafnorði.",["gulur","borð","lesa","í"])
  ])}
  if(t==="sentence"){return q("icelandic","Veldu rétt raðaða setningu.","Eva fer í skólann","Setning þarf að hljóma eðlilega.",["Eva fer í skólann","Í fer Eva skólann","Skólann Eva í fer","Fer skólann Eva í"])}
  return q("icelandic","Hvaða orð á að byrja á stórum staf?","Reykjavík","Sérnöfn byrja á stórum staf.",["Reykjavík","hundur","skóli","bolti"]);
}

function makeEnglishQuestion(){
  const vocab=[["hundur","dog"],["köttur","cat"],["skóli","school"],["vinur","friend"],["rauður","red"],["blár","blue"],["grænn","green"],["gulur","yellow"],["epli","apple"],["vatn","water"],["bók","book"],["hús","house"],["fugl","bird"],["fiskur","fish"],["borð","table"],["stóll","chair"],["penni","pen"],["bolti","ball"],["bíll","car"],["mamma","mother"],["pabbi","father"]];
  const phrases=[["Good morning","Góðan daginn"],["Thank you","Takk"],["What is your name?","Hvað heitir þú?"],["See you later","Sjáumst seinna"],["How old are you?","Hvað ertu gamall/gömul?"],["I like apples.","Mér finnst epli góð."]];
  const grammar=[
    q("english","Veldu rétta setningu.","I am ten years old.","I am er rétt með I.",["I am ten years old.","I is ten years old.","I are ten years old.","Me am ten years old."]),
    q("english","Veldu rétta setningu.","She likes cats.","Í nútíð fær sögn oft s með he/she/it.",["She likes cats.","She like cats.","Her likes cats.","She liking cats."]),
    q("english","Veldu rétta setningu.","This is my book.","Orðaröðin er This is my book.",["This is my book.","This are my book.","This my is book.","Book this my is."])
  ];
  const t=pick(["toEnglish","toIcelandic","phrase","grammar","numbers","question"]);
  if(t==="toEnglish"){let [is,en]=pick(vocab);return q("english",`Hvað er „${is}“ á ensku?`,en,"Hugsaðu um algeng ensk orð.",[en,...shuffle(vocab.map(v=>v[1]).filter(x=>x!==en)).slice(0,3)])}
  if(t==="toIcelandic"){let [is,en]=pick(vocab);return q("english",`Hvað þýðir „${en}“?`,is,"Þýddu orðið yfir á íslensku.",[is,...shuffle(vocab.map(v=>v[0]).filter(x=>x!==is)).slice(0,3)])}
  if(t==="phrase"){let [en,is]=pick(phrases);return q("english",`Hvað þýðir „${en}“?`,is,"Veldu íslensku merkinguna.",[is,...shuffle(phrases.map(v=>v[1]).filter(x=>x!==is)).slice(0,3)])}
  if(t==="numbers"){const nums=[["one","1"],["two","2"],["three","3"],["four","4"],["five","5"],["six","6"],["seven","7"],["eight","8"],["nine","9"],["ten","10"],["eleven","11"],["twelve","12"]];let [word,num]=pick(nums);return q("english",`Hvaða tala er „${word}“?`,num,"Þýddu enska töluorðið.",[num,String(rand(1,12)),String(rand(1,12)),String(rand(1,12))])}
  if(t==="question"){return q("english","Hvaða spurnarorð þýðir „hvar“?","where","Where spyr um stað.",["where","what","when","who"])}
  return pick(grammar);
}

function makeScienceQuestion(){
  const facts=[
    ["Plöntur þurfa ljós til að vaxa.","satt"],["Manneskjan andar að sér súrefni.","satt"],["Ís bráðnar þegar hann hitnar.","satt"],
    ["Fiskar lifa alltaf á þurru landi.","ósatt"],["Sólin er stjarna.","satt"],["Vatn getur verið fast, fljótandi og gas.","satt"],
    ["Rætur plantna taka upp vatn.","satt"],["Tunglið lýsir sjálft eins og stjarna.","ósatt"],["Hljóð berst aldrei í lofti.","ósatt"]
  ];
  const multi=[
    q("science","Hvaða dýr er spendýr?","hestur","Spendýr gefa ungum sínum mjólk.",["hestur","lax","fluga","snigill"]),
    q("science","Hvaða líffæri dælir blóði um líkamann?","hjarta","Það slær allan daginn.",["hjarta","magi","lunga","eyra"]),
    q("science","Hvaða hluti plöntu er oft undir moldinni?","rót","Rætur taka upp vatn.",["rót","blóm","lauf","ávöxtur"]),
    q("science","Hvaða pláneta er kölluð rauða plánetan?","Mars","Mars er rauðleit pláneta.",["Mars","Júpíter","Venus","Satúrnus"]),
    q("science","Hvaða efni þurfum við til að anda?","súrefni","Líkaminn notar súrefni.",["súrefni","sand","járn","salt"]),
    q("science","Hvað kallast vatn sem fellur úr skýjum?","úrkoma","Regn og snjór eru úrkoma.",["úrkoma","jarðskjálfti","hraun","frjókorn"]),
    q("science","Hvað byrjar oftast fæðukeðju með sólarljósi?","planta","Plöntur búa til eigin fæðu með ljósi.",["planta","refur","örn","maður"])
  ];
  if(Math.random()<.35){let [text,a]=pick(facts); return q("science",`Satt eða ósatt: ${text}`,a,"Hugsaðu hvort fullyrðingin passi við náttúruna.",["satt","ósatt"])}
  return pick(multi);
}

function makeGeoQuestion(){
  const qs=[
    q("geo","Hver er höfuðborg Íslands?","Reykjavík","Höfuðborg landsins.",["Reykjavík","Akureyri","Selfoss","Keflavík"]),
    q("geo","Í hvaða heimsálfu er Ísland?","Evrópu","Ísland er í norðanverðri Evrópu.",["Evrópu","Afríku","Asíu","Suður-Ameríku"]),
    q("geo","Hvaða átt er efst á flestum kortum?","norður","Kort snúa oftast þannig.",["norður","suður","austur","vestur"]),
    q("geo","Sólin kemur upp í...","austri","Sólin kemur upp í austri og sest í vestri.",["austri","vestri","norðri","suðri"]),
    q("geo","Hvað sýnir kortalykill?","merkingu tákna á korti","Kortalykill útskýrir tákn.",["merkingu tákna á korti","hvað allir heita","bara veðrið","hvað klukkan er"]),
    q("geo","Hvaða jökull er stærstur á Íslandi?","Vatnajökull","Vatnajökull er stærsti jökull Íslands.",["Vatnajökull","Snæfellsjökull","Langjökull","Mýrdalsjökull"]),
    q("geo","Hvað kallast land umlukið vatni?","eyja","Eyja er land með vatn allt í kring.",["eyja","dalur","fjall","borg"]),
    q("geo","Hver er höfuðborg Danmerkur?","Kaupmannahöfn","Höfuðborg Danmerkur.",["Kaupmannahöfn","Osló","Stokkhólmur","Helsinki"])
  ];
  return pick(qs);
}

function generateQuestion(){
  // Notum nýja verkefnabankann oftast, en höldum innbyggðum generatorum sem varaáætlun.
  const fromBank = generateBankQuestion();
  if(fromBank && Math.random() < 0.9) return fromBank;
  const zone=state.zone==="mixed"?pick(["math","icelandic","english","science","geo"]):state.zone;
  return {math:makeMathQuestion,icelandic:makeIcelandicQuestion,english:makeEnglishQuestion,science:makeScienceQuestion,geo:makeGeoQuestion}[zone]();
}


async function loadQuestionBank(){
  try{
    const res = await fetch("/static/questions.json?ts=" + Date.now());
    if(!res.ok) throw new Error("questions.json fannst ekki");
    const data = await res.json();
    QUESTION_BANK = Array.isArray(data.questions) ? data.questions : [];
    console.log("Static question bank loaded:", QUESTION_BANK.length);
  }catch(e){
    console.warn("Náði ekki að hlaða questions.json, nota innbyggð verkefni.", e);
    QUESTION_BANK = [];
  }

  // Kennaraspurningar úr gagnagrunni. Þetta er það sem kennari bætir við á vefnum.
  try{
    if(API.token){
      const custom = await API.call("/api/questions");
      CUSTOM_QUESTION_BANK = Array.isArray(custom) ? custom : [];
      console.log("Teacher question bank loaded:", CUSTOM_QUESTION_BANK.length);
    }
  }catch(e){
    console.warn("Náði ekki að hlaða kennaraspurningum.", e);
    CUSTOM_QUESTION_BANK = [];
  }

  // Verkefnapakkar sem eru tengdir nemandanum/bekknum.
  try{
    if(API.token){
      ASSIGNED_PACKS = await API.call("/api/assigned-packs");
      PACK_QUESTION_BANK = ASSIGNED_PACKS.flatMap(p => (p.questions || []).map(q => ({...q, packTitle:p.title, packId:p.id})));
      console.log("Assigned pack questions loaded:", PACK_QUESTION_BANK.length);
    }
  }catch(e){
    console.warn("Náði ekki að hlaða verkefnapökkum.", e);
    ASSIGNED_PACKS = [];
    PACK_QUESTION_BANK = [];
  }
}



async function loadMySkillStats(){
  try{
    if(API.token && API.user?.role === "student"){
      MY_SKILL_STATS = await API.call("/api/me/skills");
    }
  }catch(e){
    console.warn("Náði ekki að hlaða færnistöðu nemanda.", e);
    MY_SKILL_STATS = [];
  }
}

function weakSkillTargets(){
  const grade = effectiveGradeLevel ? effectiveGradeLevel() : 5;
  const stats = (MY_SKILL_STATS || []).filter(s => Number(s.grade_level || grade) === grade && s.answered >= 3);
  const weak = stats.filter(s => s.accuracy < 75).sort((a,b)=>a.accuracy-b.accuracy || b.answered-a.answered).slice(0,5);
  return weak.map(s => `${s.subject}|||${s.skill}`);
}

function adaptiveQuestionScore(item){
  if(!state.adaptiveMode) return 0;
  const key = `${item.subject}|||${item.skill || "almennt"}`;
  const weak = weakSkillTargets();
  if(weak.includes(key)) return 100;
  // prefer grade-level unseen skills a little
  const seen = (MY_SKILL_STATS || []).find(s => s.subject === item.subject && s.skill === (item.skill || "almennt") && Number(s.grade_level) === Number(item.grade_level || effectiveGradeLevel()));
  if(!seen) return 15;
  if(seen.accuracy < 85) return 25;
  return 0;
}

function setAdaptiveMode(on){
  state.adaptiveMode = !!on;
  localStorage.setItem("sr_adaptive_mode", state.adaptiveMode ? "1" : "0");
  updateUI();
  toast(state.adaptiveMode ? "Snjallæfing virk: kerfið velur veikustu færni oftar." : "Snjallæfing slökkt.");
  nextQuestion();
}

function effectiveGradeLevel(){
  if(state.gradeLevel && state.gradeLevel !== "adaptive") return Number(state.gradeLevel);
  if(state.level >= 8) return 7;
  if(state.level >= 4) return 6;
  return 5;
}
function setGradeLevel(value){
  state.gradeLevel = value;
  localStorage.setItem("sr_grade_level", value);
  updateUI();
  saveProgress();
  toast(value === "adaptive" ? "Sjálfvirkt þyngdarstig virkt." : `Þyngdarstig: ${value}. bekkur`);
  nextQuestion();
}
function questionMatchesGrade(item){
  const g = Number(item.grade_level || item.gradeLevel || item.grade || 5);
  const target = effectiveGradeLevel();
  if(state.gradeLevel === "adaptive") return g <= target && g >= Math.max(5, target - 1);
  return g === target;
}

function generateBankQuestion(){
  const combined = [...PACK_QUESTION_BANK, ...CUSTOM_QUESTION_BANK, ...QUESTION_BANK];
  if(!combined.length) return null;
  const allowed = state.zone === "mixed" ? ["math","icelandic","english","science","geo"] : [state.zone];
  const gradeFiltered = combined.filter(x => allowed.includes(x.subject) && questionMatchesGrade(x));
  const fallback = combined.filter(x => allowed.includes(x.subject));
  const sourcePool = gradeFiltered.length ? gradeFiltered : fallback;

  const packPool = PACK_QUESTION_BANK.filter(x => allowed.includes(x.subject) && questionMatchesGrade(x));
  const customPool = CUSTOM_QUESTION_BANK.filter(x => allowed.includes(x.subject) && questionMatchesGrade(x));
  const allPool = sourcePool;
  if(!allPool.length) return null;

  // Verkefnapakkar fá mesta vægi, svo kennari geti stýrt æfingu vikunnar.
  let pool = allPool;
  const roll = Math.random();
  if(packPool.length && roll < 0.70) pool = packPool;
  else if(customPool.length && roll < 0.88) pool = customPool;

  let item = pick(pool);
  if(state.adaptiveMode && pool.length){
    const boosted = pool
      .map(q => ({q, score: adaptiveQuestionScore(q) + Math.random()*10}))
      .sort((a,b)=>b.score-a.score);
    if(boosted[0] && boosted[0].score > 20) item = boosted[0].q;
  }
  return {
    subject: item.subject,
    text: item.packTitle ? `📦 ${item.packTitle}: ${item.text}` : item.text,
    answer: String(item.answer),
    hint: item.hint || "Hugsaðu málið og prófaðu aftur.",
    options: item.options && item.options.length ? shuffle(item.options.map(String)) : null,
    skill: item.skill || "almennt",
    difficulty: item.difficulty || 1,
    grade_level: item.grade_level || item.gradeLevel || 5
  };
}


/* ---------- innskráning og vistun ---------- */
async function login(){
  const msg=document.getElementById("loginMsg"); msg.textContent="";
  try{
    const data=await API.call("/api/login",{method:"POST",body:JSON.stringify({username:username.value,password:password.value})});
    API.token=data.token; API.user=data.user; localStorage.setItem("sr_token",API.token);
    await boot();
  }catch(e){msg.textContent=e.message}
}
async function logout(){try{await API.call("/api/logout",{method:"POST"})}catch{} localStorage.removeItem("sr_token"); location.reload();}
async function boot(){
  try{
    API.user = await API.call("/api/me");
    await loadQuestionBank();
    const p = await API.call("/api/progress");
    state={...state,...p, owned:p.owned||{}, achievements:p.achievements||{}, current:null};
    setupDaily();
    const savedGrade = localStorage.getItem("sr_grade_level");
    if(savedGrade) state.gradeLevel = savedGrade;
    state.adaptiveMode = localStorage.getItem("sr_adaptive_mode") === "1";
    await loadMySkillStats();
    loginScreen.classList.add("hidden"); topbar.classList.remove("hidden"); app.classList.remove("hidden");
    whoami.textContent=`${API.user.display_name} · ${API.user.role==="teacher"?"kennari":"nemandi"}`;
    document.querySelectorAll(".teacher-only").forEach(x=>x.classList.toggle("hidden",API.user.role!=="teacher"));
    updateUI(); renderShop(); renderAchievements(); if(API.user.role==="teacher") await loadTeacher();
  }catch(e){localStorage.removeItem("sr_token");}
}
async function saveProgress(){
  const payload={...state, owned:state.owned||{}, achievements:state.achievements||{}};
  delete payload.current; delete payload.user_id; delete payload.updated_at; delete payload.owned_json; delete payload.achievements_json;
  try{await API.call("/api/progress",{method:"POST",body:JSON.stringify(payload)})}catch(e){toast("Náði ekki að vista: "+e.message)}
}
async function logAttempt(payload){try{await API.call("/api/attempts",{method:"POST",body:JSON.stringify(payload)})}catch(e){}}

/* ---------- spilun ---------- */
function startMission(){nextQuestion();toast("Mission byrjað!")}
function nextQuestion(){state.current=generateQuestion();renderQuestion();}
function renderQuestion(){
  const c=state.current; if(!c)return;
  subjectBadge.textContent=`${SUBJECTS[c.subject].icon} ${SUBJECTS[c.subject].name}`;
  questionText.textContent=c.text; hintText.textContent=""; feedback.textContent=""; feedback.className="feedback";
  answers.innerHTML=""; textAnswerBox.classList.add("hidden");
  if(c.options){answers.style.display="grid"; c.options.forEach(opt=>{let b=document.createElement("button");b.textContent=opt;b.onclick=()=>answer(opt);answers.appendChild(b)})}
  else{answers.style.display="none"; textAnswerBox.classList.remove("hidden"); textAnswer.value=""; textAnswer.focus();}
}
function submitTextAnswer(){if(textAnswer.value.trim()) answer(textAnswer.value)}
async function answer(val){
  if(!state.current)return toast("Byrjaðu mission fyrst.");
  const correct=normalize(val)===normalize(state.current.answer);
  state.total_answered++;
  let xpGain=0, coinGain=0;
  if(correct){
    xpGain=Math.round((28+Math.min(state.streak*2,24))*(SUBJECTS[state.zone].xpBonus||1));
    coinGain=35+Math.min(state.streak*5,55);
    state.streak++; state.total_correct++; state.xp+=xpGain; state.coins+=coinGain;
    feedback.textContent=`Rétt! +${xpGain} XP og +${coinGain} coins 🚀`; feedback.classList.add("ok");
    document.querySelector(".question-card").classList.add("pulse-good");
    setTimeout(()=>document.querySelector(".question-card").classList.remove("pulse-good"),500);
    burst(["⭐","⚡","🎯","💥"]);
    if(state.streak === 3 || state.streak === 7 || state.streak % 12 === 0){
      state.loot_boxes++;
      showLootModal("🎁", "Streak loot!", `Þú náðir ${state.streak} í röð og fékkst loot kassa.`);
    }
    if(state.bossMode){
      state.bossLeft--;
      updateBossUI();
      if(state.bossLeft <= 0){
        winBossFight();
      }
    }
    while(state.xp>=xpNeeded()){state.xp-=xpNeeded();state.level++;state.coins+=120;toast(`Level up! Level ${state.level} · +120 coins`);burst(["👑","⭐","🚀","🏆"])}
  } else {
    if(state.bossMode){
      updateBossUI();
    }
    if(state.shields>0){state.shields--; feedback.textContent=`Ekki alveg, en skjöldur bjargaði streakinu. Rétta svarið var: ${state.current.answer}`;}
    else{state.streak=0; feedback.textContent=`Ekki alveg. Rétta svarið var: ${state.current.answer}`;}
    feedback.classList.add("bad");
  }
  updateDaily(correct);
  if(API.user?.role === "student" && state.total_answered % 3 === 0) loadMySkillStats();
  checkAchievements();
  await logAttempt({
    subject:state.current.subject,
    skill:state.current.skill || "almennt",
    difficulty:state.current.difficulty || 1,
    grade_level:state.current.grade_level || effectiveGradeLevel(),
    question:state.current.text,
    answer_given:String(val),
    correct_answer:state.current.answer,
    correct,
    xp_gain:xpGain,
    coin_gain:coinGain
  });
  updateUI(); await saveProgress(); setTimeout(nextQuestion, correct?1100:1900);
}
function useHint(){if(!state.current)return toast("Byrjaðu mission fyrst."); if(state.hints<=0)return toast("Engin vísbending eftir."); state.hints--; hintText.textContent="💡 "+state.current.hint; updateUI(); saveProgress();}
function useSkip(){if(state.skips<=0)return toast("Engin skipti eftir."); state.skips--; nextQuestion(); updateUI(); saveProgress();}

function startBossFight(){
  if(state.level < 3 && state.total_correct < 10){
    toast("Boss Fight opnast eftir level 3 eða 10 rétt svör.");
    showView("boss");
    return;
  }
  state.bossMode = true;
  state.bossMax = 5;
  state.bossLeft = 5;
  showView("mission");
  nextQuestion();
  updateBossUI();
  toast("👑 Boss Fight byrjað! Náðu 5 réttum svörum.");
}

function winBossFight(){
  state.bossMode = false;
  state.bossLeft = 0;
  state.boss_wins = (state.boss_wins || 0) + 1;
  state.coins += (subjectBosses[state.zone]?.reward || 450);
  state.xp += 220;
  state.loot_boxes += 2;
  showLootModal(subjectBosses[state.zone]?.icon || "👑", `${subjectBosses[state.zone]?.name || "Boss"} sigraður!`, `+${subjectBosses[state.zone]?.reward || 450} coins, +220 XP og 2 loot kassar!`);
  burst(["👑","🏆","⚡","💎","🎉"]);
  updateBossUI();
}

function updateBossUI(){
  const fill = document.getElementById("bossHealthFill");
  const txt = document.getElementById("bossProgressText");
  const mini = document.getElementById("bossMini");
  const unlocked = state.level >= 3 || state.total_correct >= 10;
  if(fill){
    const left = state.bossMode ? state.bossLeft : (unlocked ? 5 : 0);
    const pct = state.bossMode ? Math.max(0, (state.bossLeft / state.bossMax) * 100) : (unlocked ? 100 : 0);
    fill.style.width = pct + "%";
  }
  if(txt){
    txt.textContent = state.bossMode ? `${state.bossLeft} rétt svör eftir til sigurs.` : (unlocked ? "Boss Fight er opinn!" : "Boss Fight opnast eftir level 3 eða 10 rétt svör.");
  }
  if(mini){
    mini.textContent = state.bossMode ? `👑 Boss: ${state.bossLeft} eftir` : (unlocked ? "👑 Boss: opinn" : "👑 Boss: læstur");
  }
}

function setZone(z){state.zone=z; showView("mission"); nextQuestion(); updateUI(); saveProgress(); toast("Valið: "+SUBJECTS[z].name);}

/* ---------- daily og afrek ---------- */

function claimDailyLoginReward(){
  const today = new Date().toISOString().slice(0,10);
  if(dailyLogin && dailyLogin.date === today){
    toast("Þú ert búin/n að sækja daglega bónusinn í dag.");
    return;
  }
  const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0,10);
  const streak = dailyLogin && dailyLogin.date === yesterday ? (dailyLogin.streak || 0) + 1 : 1;
  const coins = 80 + Math.min(streak * 25, 250);
  const xp = 40 + Math.min(streak * 15, 150);
  state.coins += coins;
  state.xp += xp;
  if(streak % 5 === 0) state.loot_boxes++;
  dailyLogin = {date: today, streak};
  localStorage.setItem("sr_daily_login", JSON.stringify(dailyLogin));
  showLootModal("🎁", "Daglegur bónus!", `Streak dagur ${streak}: +${coins} coins og +${xp} XP${streak%5===0 ? " og loot kassi!" : ""}`);
  updateUI();
  saveProgress();
}

function renderDailyRewards(){
  const title = document.getElementById("dailyTitle");
  const detail = document.getElementById("dailyDetail");
  const fill = document.getElementById("dailyProgressFill");
  const track = document.getElementById("rewardTrack");
  if(!title || !detail || !fill || !track || !daily) return;
  const progress = Math.min(daily.progress, daily.goal.target);
  title.textContent = "Daily Quest";
  detail.textContent = `${daily.goal.text} (${progress}/${daily.goal.target}) · Verðlaun ${daily.goal.reward} coins`;
  fill.style.width = ((progress / daily.goal.target) * 100) + "%";
  const streak = dailyLogin?.streak || 0;
  track.innerHTML = [1,2,3,4,5,6,7].map(day => `
    <div class="reward-day ${streak >= day ? "done" : ""}">
      <strong>Dagur ${day}</strong>
      <span>${day % 5 === 0 ? "🎁 Loot" : "💰 Coins"}</span>
    </div>
  `).join("");
}

function setupDaily(){
  const today=new Date().toISOString().slice(0,10);
  if(!daily || daily.date!==today){
    daily={date:today, goal:pick(dailyOptions), progress:0, rewarded:false};
    localStorage.setItem("sr_daily",JSON.stringify(daily));
  }
}
function updateDaily(correct){
  if(!daily) return;
  if(daily.goal.id==="correct5" && correct) daily.progress++;
  if(daily.goal.id==="streak3") daily.progress=Math.max(daily.progress,state.streak);
  if(daily.goal.id==="answer10") daily.progress++;
  if(!daily.rewarded && daily.progress>=daily.goal.target){
    daily.rewarded=true; state.coins+=daily.goal.reward; toast(`Daily Quest lokið! +${daily.goal.reward} coins 🎉`); burst(["🎯","🏆","⭐"]);
  }
  localStorage.setItem("sr_daily",JSON.stringify(daily));
}
function checkAchievements(){
  achievementDefs.forEach(a=>{
    if(!state.achievements[a.id] && a.check()){
      state.achievements[a.id]=true; state.coins+=a.reward;
      toast(`🏆 Afrek opnað: ${a.title}! +${a.reward} coins`);
      burst(["🏆","⭐","🎉"]);
    }
  });
}
function renderAchievements(){
  const grid=document.getElementById("achievementGrid"); if(!grid)return;
  grid.innerHTML="";
  achievementDefs.forEach(a=>{
    const done=!!state.achievements[a.id];
    const card=document.createElement("div");
    card.className="shop-item "+(done?"achievement-done":"achievement-locked");
    card.innerHTML=`<div style="font-size:3rem">${a.icon}</div><h3>${a.title}</h3><p>${a.desc}</p><span class="price">${done?"Lokið ✅":"Verðlaun: "+a.reward+" coins"}</span>`;
    grid.appendChild(card);
  });
}

/* ---------- búð ---------- */
function renderShop(){
  shopGrid.innerHTML="";
  shopItems.forEach(item=>{
    const owned=state.owned?.[item.id];
    const card=document.createElement("div"); 
    card.className=`shop-item shop-${item.rarity || "common"}`;
    card.innerHTML=`<div class="rarity">${(item.rarity || "common").toUpperCase()}</div><div style="font-size:3rem">${item.icon}</div><h3>${item.title}</h3><p>${item.desc}</p><small class="shop-kind">${item.kind}</small><br><span class="price">${owned?"Keypt ✅":item.price+" coins"}</span><br><br><button>${owned?"Virkja":"Kaupa"}</button>`;
    card.querySelector("button").onclick=()=>buyItem(item.id); shopGrid.appendChild(card);
  });
  renderCollection();
}
function buyItem(id){
  const item=shopItems.find(x=>x.id===id); if(!item)return;
  if(["cosmetic","pet","theme"].includes(item.kind) && state.owned?.[id]){
    if(item.kind==="cosmetic") activateCosmetic(id);
    if(item.kind==="pet") activatePet(id);
    if(item.kind==="theme") activateTheme(id);
    return;
  }
  if(state.coins<item.price)return toast("Þig vantar fleiri coins.");
  state.coins-=item.price;
  state.owned = state.owned || {};
  state.pets = state.pets || {};
  state.collectibles = state.collectibles || {};
  if(id==="shield")state.shields++;
  if(id==="hint")state.hints++;
  if(id==="skip")state.skips++;
  if(id==="firststep"){ state.hints += 2; showLootModal("🔎","Fyrsta skref!","Þú fékkst 2 sér-vísbendingar."); }
  if(id==="remove2"){ state.skips += 1; state.hints += 1; showLootModal("🎯","Markhjálp!","Þú fékkst 1 skipti og 1 vísbendingu."); }
  if(id==="loot"){ state.loot_boxes++; openLootBox(); }
  if(id==="focus"){ state.xp+=150; showLootModal("🧠","Fókus-bónus!","+150 XP"); }
  if(id==="double"){ state.xp+=300; showLootModal("⚡","Rafmagns XP!","+300 XP og confetti stormur!"); burst(["⚡","⚡","⭐","💥"]); }
  if(item.kind==="cosmetic"){ state.owned[id]=true; activateCosmetic(id); showLootModal(item.icon, `${item.title} keypt!`, "Avatarinn þinn fékk nýtt útlit."); }
  if(item.kind==="pet"){ state.owned[id]=true; state.pets[id]={level:1,xp:0}; activatePet(id); showLootModal(item.icon, `${item.title} fylgir þér!`, "Lukkudýrið þitt getur levelað upp með vinnu."); }
  if(item.kind==="theme"){ state.owned[id]=true; activateTheme(id); showLootModal(item.icon, `${item.title} virkjað!`, "Vefurinn fékk nýtt þema."); }
  updateUI(); renderShop(); renderCollection(); saveProgress();
}

function activateCosmetic(id){
  if(id==="crown") avatarBox.textContent="👑";
  if(id==="dragon") avatarBox.textContent="🐉";
  if(id==="ninja") avatarBox.textContent="🥷";
  state.activeAvatar = id;
  toast("Avatar virkjaður!");
}

function openLootBox(){
  state.collectibles = state.collectibles || {};
  const roll=pick(["coins","shield","hint","skip","xp","collectible"]);
  if(roll==="coins"){let c=rand(120,420); state.coins+=c; showLootModal("💰","Loot: Coins!",`Þú fékkst ${c} coins!`)}
  if(roll==="shield"){state.shields++; showLootModal("🛡️","Loot: Skjöldur!","Þú fékkst einn skjöld.")}
  if(roll==="hint"){state.hints+=2; showLootModal("💡","Loot: Vísbendingar!","Þú fékkst 2 vísbendingar.")}
  if(roll==="skip"){state.skips+=2; showLootModal("⏭️","Loot: Mission skipti!","Þú fékkst 2 mission skipti.")}
  if(roll==="xp"){let xp=rand(90,260); state.xp+=xp; showLootModal("⭐","Loot: XP!",`Þú fékkst ${xp} XP!`)}
  if(roll==="collectible"){
    const item = awardCollectible();
    if(item) showLootModal(item.icon, `Safngripur: ${item.title}!`, `Sjaldgæfur hlutur bættist í safnið þitt (${item.rarity}).`);
    else {let c=300; state.coins+=c; showLootModal("💰","Safnið fullt!","Þú átt alla safngripi og fékkst 300 coins í staðinn.");}
  }
  renderCollection();
}

function showLootModal(icon,title,text){
  const modal=document.getElementById("lootModal");
  if(!modal){toast(text);return;}
  lootIcon.textContent=icon; lootTitle.textContent=title; lootText.textContent=text;
  modal.classList.remove("hidden");
}

function closeLootModal(){
  const modal=document.getElementById("lootModal");
  if(modal) modal.classList.add("hidden");
}

/* ---------- viðmót ---------- */
function showView(id){
  document.querySelectorAll(".view").forEach(v=>v.classList.remove("active"));
  document.getElementById("view-"+id).classList.add("active");
  document.querySelectorAll(".menu").forEach(b=>b.classList.remove("active"));
  if(id==="teacher") loadTeacher();
  if(id==="questions") loadTeacherQuestions();
  if(id==="packs") loadMissionPacks();
  if(id==="reports") loadReportsView();
  if(id==="learningpaths") loadLearningPaths();
  if(id==="pathmap") loadStudentLearningPaths();
  if(id==="boss") updateBossUI();
  if(id==="daily") renderDailyRewards();
  if(id==="achievements") renderAchievements();
}

function activateTheme(id){
  document.body.classList.remove("theme-space","theme-lava","theme-ice");
  if(id==="theme_space") document.body.classList.add("theme-space");
  if(id==="theme_lava") document.body.classList.add("theme-lava");
  if(id==="theme_ice") document.body.classList.add("theme-ice");
  state.activeTheme = id;
  toast("Þema virkjað!");
}

function activatePet(id){
  state.activePet = id;
  const item = shopItems.find(x=>x.id===id);
  toast(`${item ? item.icon : "🐾"} Lukkudýr virkjað!`);
  updateUI();
  saveProgress();
}

function awardCollectible(){
  const missing = collectibleItems.filter(c => !state.collectibles?.[c.id]);
  if(!missing.length) return null;
  const item = pick(missing);
  state.collectibles = state.collectibles || {};
  state.collectibles[item.id] = true;
  return item;
}

function renderCollection(){
  const box = document.getElementById("collectionBox");
  if(!box) return;
  const owned = collectibleItems.filter(c => state.collectibles?.[c.id]);
  box.innerHTML = owned.length ? owned.map(c=>`<span class="collection-pill ${c.rarity}">${c.icon} ${c.title}</span>`).join("") : "<p>Engir safngripir komnir enn. Opnaðu loot kassa!</p>";
}

function updateUI(){
  levelVal.textContent=state.level; xpVal.textContent=`${state.xp}/${xpNeeded()}`; coinVal.textContent=state.coins; streakVal.textContent=state.streak; correctVal.textContent=state.total_correct;
  xpBar.style.width=Math.min(100,state.xp/xpNeeded()*100)+"%";
  playerTitle.textContent=state.level>=8?"Legendary Learner":state.level>=5?"Skólahetja":state.level>=3?"Stormhlaupari":"Nýliði";
  if(state.activeAvatar==="dragon" && state.owned?.dragon) avatarBox.textContent="🐉";
  else if(state.activeAvatar==="ninja" && state.owned?.ninja) avatarBox.textContent="🥷";
  else if(state.owned?.crown) avatarBox.textContent="👑"; 
  else avatarBox.textContent=state.level>=5?"🛡️":state.level>=3?"🏃":"🪂";

  const dq=document.getElementById("dailyQuest");
  if(dq && daily) dq.textContent=`${Math.min(daily.progress,daily.goal.target)}/${daily.goal.target}`;
  const inv=document.getElementById("inventoryMini");
  if(inv) inv.textContent=`🎒 Skjöldur ${state.shields} · 💡 ${state.hints} · ⏭️ ${state.skips} · 🎁 ${state.loot_boxes || 0}`;
  const streakMiniEl=document.getElementById("streakMini");
  if(streakMiniEl) streakMiniEl.textContent=state.streak;
  const adaptiveBox=document.getElementById("adaptiveModeCheck");
  if(adaptiveBox) adaptiveBox.checked = !!state.adaptiveMode;
  const adaptiveHint=document.getElementById("adaptiveHint");
  if(adaptiveHint) adaptiveHint.textContent = state.adaptiveMode ? "Snjallæfing velur veikustu færni oftar." : "Slökkt: verkefni veljast meira handahófskennt.";
  const gradeEl=document.getElementById("gradeMini");
  if(gradeEl) gradeEl.textContent = state.gradeLevel === "adaptive" ? `Sjálfvirkt (${effectiveGradeLevel()}. bekkur)` : `${effectiveGradeLevel()}. bekkur`;
  const gradeSelect=document.getElementById("gradeLevelSelect");
  if(gradeSelect) gradeSelect.value = state.gradeLevel || "5";
  const gradeHint=document.getElementById("gradeLevelHint");
  if(gradeHint) gradeHint.textContent = state.gradeLevel === "adaptive" ? "Kerfið hækkar þyngd eftir árangri." : `Verkefni miða við ${effectiveGradeLevel()}. bekk.`;
  const petEl=document.getElementById("activePetInfo");
  if(petEl){
    const pet = shopItems.find(x=>x.id===state.activePet);
    petEl.textContent = pet ? `${pet.icon} ${pet.title}` : "Ekkert lukkudýr";
  }
  renderCollection();
  const zoneEl=document.getElementById("currentZoneName");
  if(zoneEl) zoneEl.textContent=SUBJECTS[state.zone]?.name || state.zone;
  const packEl=document.getElementById("activePackInfo");
  if(packEl) packEl.textContent=ASSIGNED_PACKS && ASSIGNED_PACKS.length ? `${ASSIGNED_PACKS.length} virkir` : "Enginn valinn";
  updateBossUI();
  renderDailyRewards();
  renderAchievements();
}
function toast(msg){const t=document.getElementById("toast");t.textContent=msg;t.classList.add("show");clearTimeout(window.toastTimer);window.toastTimer=setTimeout(()=>t.classList.remove("show"),2600)}
function burst(symbols){
  for(let i=0;i<18;i++){
    const s=document.createElement("div"); s.className="confetti"; s.textContent=pick(symbols);
    s.style.left=Math.random()*100+"vw"; s.style.animationDuration=(1.2+Math.random()*1.5)+"s"; s.style.fontSize=(18+Math.random()*18)+"px";
    document.body.appendChild(s); setTimeout(()=>s.remove(),3100);
  }
}

/* ---------- kennari ---------- */
async function createStudent(){
  createMsg.textContent="";
  try{
    await API.call("/api/teacher/students",{method:"POST",body:JSON.stringify({username:newUsername.value,display_name:newName.value,password:newPassword.value,class_name:newClass.value})});
    createMsg.textContent=" Nemandi stofnaður ✅"; newUsername.value=""; newName.value=""; newPassword.value=""; newClass.value=""; await loadTeacher();
  }catch(e){createMsg.textContent=" "+e.message}
}

let teacherStudentsCache = [];
let teacherSubjectsCache = [];
let teacherSkillsCache = [];
let teacherNeedsCache = [];

async function createBulkStudents(){
  bulkMsg.textContent="";
  const lines = bulkStudents.value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean);
  const students = [];
  for(const line of lines){
    const parts = line.split(",").map(x=>x.trim());
    if(parts.length < 3){ bulkMsg.textContent = "Villa: lína þarf að vera notandanafn,nafn,lykilorð,bekkur"; return; }
    students.push({username:parts[0], display_name:parts[1], password:parts[2], class_name:parts[3]||""});
  }
  try{
    const res = await API.call("/api/teacher/students/bulk",{method:"POST",body:JSON.stringify({students})});
    bulkMsg.textContent = ` Stofnaðir: ${res.created.length}. Villur: ${res.errors.length}.`;
    bulkStudents.value="";
    await loadTeacher();
  }catch(e){bulkMsg.textContent=" "+e.message}
}

async function loadTeacher(){
  if(!API.user || API.user.role!=="teacher")return;
  teacherStudentsCache=await API.call("/api/teacher/students");
  teacherSubjectsCache=await API.call("/api/teacher/subject-summary");
  const classes = await API.call("/api/teacher/classes");
  const old = classFilter?.value || "";
  if(classFilter){
    classFilter.innerHTML = '<option value="">Allir bekkir</option>' + classes.map(c=>`<option value="${c.class_name}">${c.class_name} (${c.students})</option>`).join("");
    classFilter.value = old;
  }
  await loadSkillDashboard();
  renderTeacherFromCache();
}


async function loadSkillDashboard(){
  const selected = classFilter?.value || "";
  const qs = selected ? `?class_name=${encodeURIComponent(selected)}` : "";
  teacherSkillsCache = await API.call("/api/teacher/skill-summary" + qs);
  teacherNeedsCache = await API.call("/api/teacher/skill-needs" + qs);
}

function renderSkillDashboard(){
  const needs = document.getElementById("skillNeeds");
  const table = document.getElementById("skillTable");
  if(!needs || !table) return;

  if(!teacherSkillsCache.length){
    needs.innerHTML = "<p>Engin færnigögn komin enn. Láttu nemendur svara nokkrum verkefnum.</p>";
    table.innerHTML = "";
    const c = document.getElementById("skillChart");
    if(c){ const ctx=c.getContext("2d"); ctx.clearRect(0,0,c.width,c.height); }
    return;
  }

  needs.innerHTML = `
    <div class="needs-grid">
      ${teacherNeedsCache.slice(0,6).map((n,i)=>`
        <div class="need-card">
          <strong>${i+1}. ${SUBJECTS[n.subject]?.name || n.subject}</strong>
          <span>${escapeHtml(n.skill)}</span>
          <b>${n.accuracy}% rétt</b>
          <small>${n.answered} svör · ${n.students} nem.</small>
        </div>`).join("")}
    </div>
  `;

  const sorted = [...teacherSkillsCache].sort((a,b)=>a.accuracy-b.accuracy || b.answered-a.answered);
  table.innerHTML = `<table class="table"><thead><tr><th>Grein</th><th>Færni</th><th>Svarað</th><th>Rétt</th><th>Nákvæmni</th><th>Staða</th></tr></thead><tbody>
    ${sorted.map(s=>`<tr>
      <td>${SUBJECTS[s.subject]?.name || s.subject}</td>
      <td>${escapeHtml(s.skill)}</td>
      <td>${s.answered}</td>
      <td>${s.correct}</td>
      <td>${s.accuracy}%</td>
      <td>${skillStatus(s.accuracy, s.answered)}</td>
    </tr>`).join("")}
  </tbody></table>`;

  const chartItems = sorted.slice(0,12);
  drawBarChart("skillChart", chartItems.map(s=>`${SUBJECTS[s.subject]?.name || s.subject}: ${s.skill}`), chartItems.map(s=>s.accuracy), "Færni sem þarf mest að æfa (%)");
}

function skillStatus(acc, answered){
  if(answered < 3) return "🟦 of fá svör";
  if(acc >= 85) return "🟩 öruggt";
  if(acc >= 65) return "🟨 æfa aðeins";
  return "🟥 þarf æfingu";
}


function renderTeacherFromCache(){
  let students = teacherStudentsCache || [];
  const selected = classFilter?.value || "";
  if(selected) students = students.filter(s => (s.class_name || "Óflokkað") === selected);
  renderStudentTable(students);
  drawBarChart("studentChart",students.map(s=>s.display_name),students.map(s=>s.total_correct||0),"Rétt svör eftir nemanda");
  drawBarChart("subjectChart",teacherSubjectsCache.map(s=>SUBJECTS[s.subject]?.name||s.subject),teacherSubjectsCache.map(s=>s.accuracy||0),"Nákvæmni % eftir grein");
  renderSkillDashboard();
}

function renderStudentTable(students){
  studentTable.innerHTML=`<table class="table"><thead><tr><th>Nemandi</th><th>Bekkur</th><th>Level</th><th>Rétt</th><th>Svarað</th><th>Nákvæmni</th><th>Aðgerðir</th></tr></thead><tbody>${students.map(s=>`<tr><td><strong>${s.display_name}</strong><br><small>${s.username}</small></td><td>${s.class_name||"Óflokkað"}</td><td>${s.level||1}</td><td>${s.total_correct||0}</td><td>${s.total_answered||0}</td><td>${s.accuracy||0}%</td><td><button onclick="showStudentDetail(${s.id})">Skoða</button> <button onclick="resetStudentPassword(${s.id})">Nýtt lykilorð</button> <button onclick="toggleStudent(${s.id},${s.active?0:1})">${s.active?"Óvirkja":"Virkja"}</button></td></tr>`).join("")}</tbody></table>`;
}

async function showStudentDetail(id){
  currentStudentDetailId = id;
  try{
    const d = await API.call(`/api/teacher/students/${id}/detail`);
    studentDetail.classList.remove("hidden");
    studentDetail.innerHTML = `
      <h3>Nemendaskýrsla: ${d.display_name}</h3>
      <p class="no-print"><button onclick="downloadStudentReport(${id})">Sækja CSV fyrir nemanda</button> <button onclick="printCurrentStudentReport()">Prenta skýrslu</button></p>
      <p><strong>Notandanafn:</strong> ${d.username} · <strong>Bekkur:</strong> ${d.class_name || "Óflokkað"} · <strong>Nákvæmni:</strong> ${d.accuracy}%</p>
      <div class="mini-stats">
        <span>Level ${d.level||1}</span><span>${d.total_correct||0} rétt</span><span>${d.total_answered||0} svör</span><span>${d.coins||0} coins</span>
      </div>
      <h4>Greinar</h4>
      <table class="table"><thead><tr><th>Grein</th><th>Svarað</th><th>Rétt</th><th>Nákvæmni</th></tr></thead><tbody>
        ${d.subjects.map(s=>`<tr><td>${SUBJECTS[s.subject]?.name||s.subject}</td><td>${s.answered}</td><td>${s.correct}</td><td>${s.accuracy}%</td></tr>`).join("") || "<tr><td colspan='4'>Engin svör komin.</td></tr>"}
      </tbody></table>
      <h4>Færni</h4>
      <table class="table"><thead><tr><th>Grein</th><th>Færni</th><th>Svarað</th><th>Rétt</th><th>Nákvæmni</th><th>Staða</th></tr></thead><tbody>
        ${(d.skills||[]).sort((a,b)=>a.accuracy-b.accuracy).map(s=>`<tr><td>${SUBJECTS[s.subject]?.name||s.subject}</td><td>${escapeHtml(s.skill)}</td><td>${s.answered}</td><td>${s.correct}</td><td>${s.accuracy}%</td><td>${skillStatus(s.accuracy,s.answered)}</td></tr>`).join("") || "<tr><td colspan='6'>Engin færnigögn komin.</td></tr>"}
      </tbody></table>
      <h4>Síðustu svör</h4>
      <table class="table"><thead><tr><th>Grein</th><th>Færni</th><th>Spurning</th><th>Svar</th><th>Rétt svar</th><th>Staða</th></tr></thead><tbody>
        ${d.recent_attempts.map(a=>`<tr><td>${SUBJECTS[a.subject]?.name||a.subject}</td><td>${escapeHtml(a.skill||"almennt")}</td><td>${escapeHtml(a.question)}</td><td>${escapeHtml(a.answer_given||"")}</td><td>${escapeHtml(a.correct_answer||"")}</td><td>${a.correct?"✅":"❌"}</td></tr>`).join("") || "<tr><td colspan='6'>Engin svör komin.</td></tr>"}
      </tbody></table>
      <button onclick="studentDetail.classList.add('hidden')">Loka skýrslu</button>
    `;
    studentDetail.scrollIntoView({behavior:"smooth", block:"start"});
  }catch(e){toast(e.message)}
}

async function resetStudentPassword(id){
  const password = prompt("Sláðu inn nýtt lykilorð fyrir nemandann, minnst 4 stafir:");
  if(!password) return;
  if(password.length < 4) return toast("Lykilorð þarf að vera minnst 4 stafir.");
  try{
    await API.call(`/api/teacher/students/${id}/reset-password`,{method:"POST",body:JSON.stringify({password})});
    toast("Lykilorði breytt.");
  }catch(e){toast(e.message)}
}

async function toggleStudent(id, active){
  try{
    await API.call(`/api/teacher/students/${id}/active?active=${active ? "true":"false"}`,{method:"PATCH",body:JSON.stringify({})});
    await loadTeacher();
    toast(active ? "Nemandi virkjaður." : "Nemandi óvirkjaður.");
  }catch(e){toast(e.message)}
}

function drawBarChart(id, labels, values, title){
  const c=document.getElementById(id), ctx=c.getContext("2d"), w=c.width=c.clientWidth, h=c.height=230;
  ctx.clearRect(0,0,w,h); ctx.font="bold 15px Segoe UI"; ctx.fillText(title,12,22);
  const max=Math.max(1,...values), barW=Math.max(18,(w-48)/Math.max(1,values.length)-8);
  values.forEach((v,i)=>{
    const x=28+i*(barW+8), bh=(h-78)*(v/max);
    ctx.fillRect(x,h-42-bh,barW,bh);
    ctx.font="12px Segoe UI"; ctx.save(); ctx.translate(x,h-20); ctx.rotate(-0.45); ctx.fillText(String(labels[i]).slice(0,13),0,0); ctx.restore();
    ctx.font="bold 12px Segoe UI"; ctx.fillText(v,x,h-48-bh);
  });
}

async function createTeacherQuestion(){
  questionMsg.textContent = "";
  const options = qOptions.value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean);
  const payload = {
    subject: qSubject.value,
    skill: qSkill.value || "almennt",
    difficulty: Number(qDifficulty.value || 1),
    grade_level: Number(qGradeLevel.value || 5),
    text: qText.value,
    answer: qAnswer.value,
    hint: qHint.value,
    options,
    active: true
  };
  if(!payload.text.trim() || !payload.answer.trim()){
    questionMsg.textContent = " Spurning og rétt svar þurfa að vera útfyllt.";
    return;
  }
  try{
    await API.call("/api/teacher/questions",{method:"POST",body:JSON.stringify(payload)});
    questionMsg.textContent = " Spurning vistuð ✅";
    clearQuestionForm();
    await loadTeacherQuestions();
    await loadQuestionBank();
  }catch(e){
    questionMsg.textContent = " " + e.message;
  }
}

function clearQuestionForm(){
  qText.value = "";
  qAnswer.value = "";
  qHint.value = "";
  qOptions.value = "";
  qSkill.value = "";
  qDifficulty.value = "1";
}

async function loadTeacherQuestions(){
  if(!API.user || API.user.role !== "teacher") return;
  try{
    teacherQuestionsCache = await API.call("/api/teacher/questions");
    renderTeacherQuestions();
  }catch(e){
    teacherQuestionsList.innerHTML = `<p class="bad">Náði ekki að hlaða spurningum: ${e.message}</p>`;
  }
}

function renderTeacherQuestions(){
  const list = document.getElementById("teacherQuestionsList");
  if(!list) return;
  if(!teacherQuestionsCache.length){
    list.innerHTML = "<p>Engar kennaraspurningar komnar enn.</p>";
    return;
  }
  list.innerHTML = `<table class="table"><thead><tr><th>Staða</th><th>Grein</th><th>Færni</th><th>Spurning</th><th>Rétt svar</th><th>Aðgerðir</th></tr></thead><tbody>
    ${teacherQuestionsCache.map(q=>`
      <tr>
        <td>${q.active ? "✅ virk" : "⏸ óvirk"}</td>
        <td>${SUBJECTS[q.subject]?.name || q.subject}</td>
        <td>${q.skill || "almennt"}</td>
        <td>${escapeHtml(q.text)}</td>
        <td>${escapeHtml(q.answer)}</td>
        <td>
          <button onclick="toggleTeacherQuestion('${q.id}', ${q.active ? 0 : 1})">${q.active ? "Óvirkja" : "Virkja"}</button>
          <button onclick="deleteTeacherQuestion('${q.id}')">Eyða</button>
        </td>
      </tr>`).join("")}
  </tbody></table>`;
}

function numericQuestionId(id){
  return String(id).replace("custom-","");
}

async function toggleTeacherQuestion(id, active){
  try{
    await API.call(`/api/teacher/questions/${numericQuestionId(id)}`,{
      method:"PATCH",
      body:JSON.stringify({active: !!active})
    });
    await loadTeacherQuestions();
    await loadQuestionBank();
    toast(active ? "Spurning virkjuð." : "Spurning óvirkjuð.");
  }catch(e){toast(e.message)}
}

async function deleteTeacherQuestion(id){
  if(!confirm("Viltu örugglega eyða þessari spurningu?")) return;
  try{
    await API.call(`/api/teacher/questions/${numericQuestionId(id)}`,{method:"DELETE"});
    await loadTeacherQuestions();
    await loadQuestionBank();
    toast("Spurningu eytt.");
  }catch(e){toast(e.message)}
}

function escapeHtml(str){
  return String(str).replace(/[&<>"']/g, s => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"
  }[s]));
}



async function loadMissionPacks(){
  if(!API.user || API.user.role !== "teacher") return;
  try{
    // Try to ensure question picker has the latest teacher questions.
    if(!teacherQuestionsCache.length) await loadTeacherQuestions();
    missionPacksCache = await API.call("/api/teacher/packs");
    renderPackQuestionPicker();
    renderMissionPacks();
  }catch(e){
    missionPacksList.innerHTML = `<p class="bad">Náði ekki að hlaða verkefnapökkum: ${e.message}</p>`;
  }
}

function renderPackQuestionPicker(){
  const box = document.getElementById("packQuestionPicker");
  if(!box) return;
  const activeQuestions = (teacherQuestionsCache || []).filter(q => q.active);
  if(!activeQuestions.length){
    box.innerHTML = "<p>Engar virkar kennaraspurningar. Búðu fyrst til spurningar í ✍️ Spurningabanka.</p>";
    return;
  }
  box.innerHTML = activeQuestions.map(q => `
    <label class="picker-row">
      <input type="checkbox" value="${numericQuestionId(q.id)}">
      <span><strong>${SUBJECTS[q.subject]?.name || q.subject}</strong> · ${escapeHtml(q.skill || "almennt")}<br>${escapeHtml(q.text)}</span>
    </label>
  `).join("");
}

async function createMissionPack(){
  packMsg.textContent = "";
  const ids = [...document.querySelectorAll("#packQuestionPicker input:checked")].map(x => Number(x.value));
  if(!packTitle.value.trim()){
    packMsg.textContent = " Heiti vantar.";
    return;
  }
  if(!ids.length){
    packMsg.textContent = " Veldu að minnsta kosti eina spurningu.";
    return;
  }
  const payload = {
    title: packTitle.value,
    description: packDescription.value,
    class_name: packClass.value,
    question_ids: ids,
    active: true
  };
  try{
    await API.call("/api/teacher/packs",{method:"POST",body:JSON.stringify(payload)});
    packMsg.textContent = " Verkefnapakki vistaður ✅";
    clearPackForm();
    await loadMissionPacks();
    await loadQuestionBank();
  }catch(e){
    packMsg.textContent = " " + e.message;
  }
}

function clearPackForm(){
  packTitle.value = "";
  packDescription.value = "";
  packClass.value = "";
  document.querySelectorAll("#packQuestionPicker input:checked").forEach(x => x.checked = false);
}

function renderMissionPacks(){
  const list = document.getElementById("missionPacksList");
  if(!list) return;
  if(!missionPacksCache.length){
    list.innerHTML = "<p>Engir verkefnapakkar komnir enn.</p>";
    return;
  }
  list.innerHTML = missionPacksCache.map(p => `
    <div class="pack-card">
      <div>
        <h3>${p.active ? "✅" : "⏸"} ${escapeHtml(p.title)}</h3>
        <p>${escapeHtml(p.description || "")}</p>
        <div class="pack-meta">
          <span>Bekkur: ${p.class_name ? escapeHtml(p.class_name) : "allir"}</span>
          <span>${(p.questions || []).length} spurningar</span>
        </div>
      </div>
      <div class="pack-actions">
        <button onclick="toggleMissionPack(${p.id}, ${p.active ? 0 : 1})">${p.active ? "Óvirkja" : "Virkja"}</button>
        <button onclick="deleteMissionPack(${p.id})">Eyða</button>
      </div>
    </div>
  `).join("");
}

async function toggleMissionPack(id, active){
  try{
    await API.call(`/api/teacher/packs/${id}`,{
      method:"PATCH",
      body:JSON.stringify({active: !!active})
    });
    await loadMissionPacks();
    toast(active ? "Verkefnapakki virkjaður." : "Verkefnapakki óvirkjaður.");
  }catch(e){toast(e.message)}
}

async function deleteMissionPack(id){
  if(!confirm("Viltu örugglega eyða verkefnapakkanum? Spurningarnar sjálfar eyðast ekki.")) return;
  try{
    await API.call(`/api/teacher/packs/${id}`,{method:"DELETE"});
    await loadMissionPacks();
    toast("Verkefnapakka eytt.");
  }catch(e){toast(e.message)}
}



function getReportClass(){
  return document.getElementById("reportClassFilter")?.value || "";
}

function reportUrl(path){
  const cls = getReportClass();
  return cls ? `${path}?class_name=${encodeURIComponent(cls)}` : path;
}

function downloadClassReport(){
  window.open(reportUrl("/api/teacher/reports/class.csv"), "_blank");
}

function downloadSkillReport(){
  window.open(reportUrl("/api/teacher/reports/skills.csv"), "_blank");
}

function downloadStudentReport(id){
  window.open(`/api/teacher/reports/student/${id}.csv`, "_blank");
}

async function loadReportsView(){
  if(!API.user || API.user.role !== "teacher") return;
  try{
    const classes = await API.call("/api/teacher/classes");
    const select = document.getElementById("reportClassFilter");
    if(select){
      const old = select.value || "";
      select.innerHTML = '<option value="">Allir bekkir</option>' + classes.map(c=>`<option value="${c.class_name}">${c.class_name} (${c.students})</option>`).join("");
      select.value = old;
    }
    await loadSupportNeeds();
  }catch(e){
    toast("Náði ekki að hlaða skýrslusíðu: " + e.message);
  }
}

async function loadSupportNeeds(){
  const box = document.getElementById("supportNeedsList");
  if(!box) return;
  box.innerHTML = "<p>Hleð...</p>";
  try{
    const cls = getReportClass();
    const qs = cls ? `?class_name=${encodeURIComponent(cls)}` : "";
    const rows = await API.call("/api/teacher/support-needs" + qs);
    if(!rows.length){
      box.innerHTML = "<p>Engin skýr stuðningsþörf fannst miðað við núverandi gögn. Láttu nemendur svara fleiri verkefnum til að fá betri mynd.</p>";
      return;
    }
    box.innerHTML = `<table class="table"><thead><tr><th>Nemandi</th><th>Bekkur</th><th>Grein</th><th>Færni</th><th>Rétt</th><th>Svarað</th><th>Nákvæmni</th><th>Aðgerð</th></tr></thead><tbody>
      ${rows.map(r=>`<tr>
        <td><strong>${escapeHtml(r.nemandi)}</strong><br><small>${escapeHtml(r.notandanafn)}</small></td>
        <td>${escapeHtml(r.bekkur)}</td>
        <td>${SUBJECTS[r.grein]?.name || r.grein}</td>
        <td>${escapeHtml(r.faerni)}</td>
        <td>${r.rett}</td>
        <td>${r.svarad}</td>
        <td>${r.nakvaemni}%</td>
        <td><button onclick="showView('teacher'); showStudentDetail(${r.student_id})">Skoða</button></td>
      </tr>`).join("")}
    </tbody></table>`;
  }catch(e){
    box.innerHTML = `<p class="bad">${e.message}</p>`;
  }
}

function printCurrentStudentReport(){
  const detail = document.getElementById("studentDetail");
  if(!detail || detail.classList.contains("hidden")){
    toast("Opnaðu fyrst nemendaskýrslu í Mælaborði kennara.");
    return;
  }
  window.print();
}



async function loadStudentLearningPaths(){
  const box = document.getElementById("studentLearningPaths");
  if(!box) return;
  box.innerHTML = "<p>Hleð námsleiðum...</p>";
  try{
    LEARNING_PATHS = await API.call("/api/learning-paths");
    renderStudentLearningPaths();
  }catch(e){
    box.innerHTML = `<p class="bad">${e.message}</p>`;
  }
}

function renderStudentLearningPaths(){
  const box = document.getElementById("studentLearningPaths");
  if(!box) return;
  if(!LEARNING_PATHS.length){
    box.innerHTML = "<p>Engin námsleið er virk fyrir þig ennþá.</p>";
    return;
  }
  box.innerHTML = LEARNING_PATHS.map(path => `
    <div class="path-card">
      <div class="path-header">
        <h3>${path.subject === "mixed" ? "🎯" : SUBJECTS[path.subject]?.icon || "🧭"} ${escapeHtml(path.title)}</h3>
        <span>${path.grade_level}. bekkur · ${path.class_name || "allir"} · verðlaun ${path.reward_coins} coins</span>
      </div>
      <p>${escapeHtml(path.description || "")}</p>
      <div class="path-steps">
        ${(path.steps || []).map((s,i)=>`
          <div class="path-step ${s.step_type}">
            <div class="step-orb">${s.step_type === "boss" || s.boss_required ? "👑" : i+1}</div>
            <strong>${escapeHtml(s.title)}</strong>
            <small>${escapeHtml(s.description || "")}</small>
            <span>${SUBJECTS[s.subject]?.name || s.subject} · ${s.skill || "valin færni"} · ${s.target_correct} rétt</span>
            <button onclick="startLearningPathStep(${path.id}, ${s.id})">Byrja skref</button>
          </div>`).join("")}
      </div>
    </div>
  `).join("");
}

function startLearningPathStep(pathId, stepId){
  const path = LEARNING_PATHS.find(p=>p.id===pathId);
  const step = path?.steps?.find(s=>s.id===stepId);
  if(!step) return toast("Skref fannst ekki.");
  state.zone = step.subject || "mixed";
  state.gradeLevel = String(step.grade_level || path.grade_level || effectiveGradeLevel());
  localStorage.setItem("sr_grade_level", state.gradeLevel);
  state.activeLearningStep = {pathId, stepId, skill:step.skill, targetCorrect:step.target_correct, title:step.title, boss:step.boss_required};
  showView("mission");
  if(step.boss_required || step.step_type === "boss") startBossFight();
  else nextQuestion();
  toast(`Námsleið: ${step.title}`);
}

async function loadLearningPaths(){
  if(!API.user || API.user.role !== "teacher") return;
  try{
    teacherLearningPathsCache = await API.call("/api/teacher/learning-paths");
    renderLearningPathsList();
    if(!document.querySelector(".lp-step-row")) {
      addLearningPathStep("Æfing 1", "Kláraðu fyrstu æfingalotu.", "practice", 5);
      addLearningPathStep("Áskorun", "Sýndu að þú náir færninni.", "challenge", 8);
      addLearningPathStep("Boss", "Lokabardagi námsleiðarinnar.", "boss", 5, true);
    }
  }catch(e){
    const list = document.getElementById("learningPathsList");
    if(list) list.innerHTML = `<p class="bad">${e.message}</p>`;
  }
}

function addLearningPathStep(title="", desc="", type="practice", target=5, boss=false){
  const box = document.getElementById("lpStepsEditor");
  if(!box) return;
  const row = document.createElement("div");
  row.className = "lp-step-row";
  row.innerHTML = `
    <input class="lp-step-title" placeholder="Heiti skrefs" value="${escapeHtml(title)}">
    <input class="lp-step-skill" placeholder="Færni, t.d. prósentur">
    <select class="lp-step-type">
      <option value="practice">Æfing</option>
      <option value="challenge">Áskorun</option>
      <option value="boss">Boss</option>
      <option value="quiz">Lokapróf</option>
    </select>
    <input class="lp-step-target" type="number" min="1" max="100" value="${target}">
    <input class="lp-step-desc" placeholder="Lýsing" value="${escapeHtml(desc)}">
    <label><input class="lp-step-boss" type="checkbox" ${boss ? "checked" : ""}> Boss</label>
    <button onclick="this.closest('.lp-step-row').remove()">Eyða</button>
  `;
  box.appendChild(row);
  row.querySelector(".lp-step-type").value = type;
}

function collectLearningPathSteps(){
  const subject = document.getElementById("lpSubject")?.value || "mixed";
  const grade = Number(document.getElementById("lpGrade")?.value || 5);
  return [...document.querySelectorAll(".lp-step-row")].map(row => ({
    title: row.querySelector(".lp-step-title").value || "Skref",
    description: row.querySelector(".lp-step-desc").value || "",
    step_type: row.querySelector(".lp-step-type").value || "practice",
    subject,
    skill: row.querySelector(".lp-step-skill").value || "",
    grade_level: grade,
    target_correct: Number(row.querySelector(".lp-step-target").value || 5),
    boss_required: row.querySelector(".lp-step-boss").checked,
    reward_coins: row.querySelector(".lp-step-boss").checked ? 250 : 100
  }));
}

async function createLearningPath(){
  lpMsg.textContent = "";
  if(!lpTitle.value.trim()){
    lpMsg.textContent = " Heiti vantar.";
    return;
  }
  const payload = {
    title: lpTitle.value,
    description: lpDescription.value,
    class_name: lpClass.value,
    grade_level: Number(lpGrade.value || 5),
    subject: lpSubject.value,
    reward_coins: 500,
    active: true,
    steps: collectLearningPathSteps()
  };
  try{
    await API.call("/api/teacher/learning-paths",{method:"POST", body:JSON.stringify(payload)});
    lpMsg.textContent = " Námsleið vistuð ✅";
    clearLearningPathForm();
    await loadLearningPaths();
  }catch(e){
    lpMsg.textContent = " " + e.message;
  }
}

function clearLearningPathForm(){
  lpTitle.value = "";
  lpDescription.value = "";
  lpClass.value = "";
  lpGrade.value = "5";
  lpSubject.value = "mixed";
  lpStepsEditor.innerHTML = "";
  addLearningPathStep("Æfing 1", "Kláraðu fyrstu æfingalotu.", "practice", 5);
  addLearningPathStep("Áskorun", "Sýndu að þú náir færninni.", "challenge", 8);
  addLearningPathStep("Boss", "Lokabardagi námsleiðarinnar.", "boss", 5, true);
}

function renderLearningPathsList(){
  const list = document.getElementById("learningPathsList");
  if(!list) return;
  if(!teacherLearningPathsCache.length){
    list.innerHTML = "<p>Engar námsleiðir komnar enn.</p>";
    return;
  }
  list.innerHTML = teacherLearningPathsCache.map(p => `
    <div class="pack-card">
      <div>
        <h3>${p.active ? "✅" : "⏸"} ${escapeHtml(p.title)}</h3>
        <p>${escapeHtml(p.description || "")}</p>
        <div class="pack-meta">
          <span>${p.grade_level}. bekkur</span>
          <span>${SUBJECTS[p.subject]?.name || p.subject}</span>
          <span>Bekkur: ${p.class_name || "allir"}</span>
          <span>${(p.steps || []).length} skref</span>
        </div>
      </div>
      <div class="pack-actions">
        <button onclick="toggleLearningPath(${p.id}, ${p.active ? 0 : 1})">${p.active ? "Óvirkja" : "Virkja"}</button>
        <button onclick="deleteLearningPath(${p.id})">Eyða</button>
      </div>
    </div>
  `).join("");
}

async function toggleLearningPath(id, active){
  try{
    await API.call(`/api/teacher/learning-paths/${id}`,{method:"PATCH",body:JSON.stringify({active:!!active})});
    await loadLearningPaths();
    toast(active ? "Námsleið virkjuð." : "Námsleið óvirkjuð.");
  }catch(e){toast(e.message)}
}

async function deleteLearningPath(id){
  if(!confirm("Viltu örugglega eyða námsleiðinni?")) return;
  try{
    await API.call(`/api/teacher/learning-paths/${id}`,{method:"DELETE"});
    await loadLearningPaths();
    toast("Námsleið eytt.");
  }catch(e){toast(e.message)}
}


window.onload=()=>{if(API.token)boot();}
