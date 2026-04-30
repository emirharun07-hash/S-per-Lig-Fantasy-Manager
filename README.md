# S-per-Lig-Fantasy-Manager
import { useState, useEffect, useMemo, useCallback } from "react";

const T={
  de:{
    appName:"SÜPER LİG FANTASY",transferBudget:"TRANSFERBUDGET",seasonPts:"SAISONPUNKTE",
    tabTeam:"⚽ Aufstellung",tabMarket:"🔄 Transfermarkt",tabLive:"🔴 Live",
    tabRanking:"🏆 Rangliste",tabRules:"📋 Punkte",
    formation:"FORMATION",selectPlayer:"KADER",teamFull:"Team voll (11/11)!",
    alreadyIn:"Bereits in Startelf!",positionFull:"Position voll!",
    added:"in Startelf ✓",removed:"aus Startelf",
    marketTitle:"TRANSFERMARKT",marketSub:"30 Spieler — Verdeckte Gebote",
    blindNotice:"🔒 Niemand sieht dein Gebot. Höchstgebot gewinnt.",
    bidPlaceholder:"Gebot (Mio. €)",submitBid:"Gebot abgeben",
    bidDone:"✓ Gebot abgegeben",bidResult:"Ergebnis bei Ablauf",
    refresh:"Neu laden",invalidBid:"Gültiges Gebot eingeben!",
    bidPlaced:"Gebot abgegeben!",noBudgetBid:"Nicht genug Budget!",
    liveTitle:"LIVE SPIELTAG",liveSub:"Süper Lig — Echte Spielerdaten",
    myMatchPts:"MATCHPUNKTE",myPlayers:"aktive Spieler",
    eventsTitle:"EREIGNISSE",startBtn:"▶ Starten",pauseBtn:"⏸ Pause",
    restartBtn:"🔄 Neustart",resetBtn:"↺ Reset",
    noEvents:"Starten für Simulation",myPlayer:"★ Dein Spieler",
    rankTitle:"RANGLISTE",rankSub:"Saison 2024/25",
    weekCol:"SPIELTAG",seasonCol:"GESAMT",managerCol:"MANAGER",
    rulesTitle:"PUNKTESYSTEM",rulesSub:"Live aus echten Spielerdaten",
    langTitle:"SPRACHE WÄHLEN",all:"Alle",
    assignedSquad:"KADER (15)",squadNote:"Tippe zum Hinzufügen",
    tierStar:"⭐ Star",tierStarter:"Starter",tierRotation:"Rotation",tierBench:"Bank",
    posGK:"TW",posDEF:"DEF",posMF:"MF",posFW:"ST",
    sortVal:"Wert",sortForm:"Form",sortName:"Name",
    searchPlayer:"Suchen...",filterClub:"Verein",
    sellToMarket:"Zum Marktwert verkaufen",sellToManagers:"An Manager verkaufen",
    listForSale:"Anbieten",listPrice:"Preis (Mio. €)",confirmSell:"Verkaufen",
    cancelSell:"Abbrechen",soldNotif:"verkauft!",listedNotif:"angeboten!",
    alreadyListed:"Bereits angeboten!",myListings:"MEINE ANGEBOTE",
    noListings:"Keine Angebote",sellMode:"💸",listedTag:"Angeboten",listedFor:"Preis",
    mwInfo:"Marktwert ändert sich täglich je nach Käufen/Verkäufen",
    mwChange:"Marktwert-Änderung",mwUp:"↑ steigt",mwDown:"↓ fällt",mwStable:"→ stabil",
  },
  tr:{
    appName:"SÜPER LİG FANTASY",transferBudget:"TRANSFER BÜTÇESİ",seasonPts:"SEZON PUANI",
    tabTeam:"⚽ Kadro",tabMarket:"🔄 Transfer",tabLive:"🔴 Canlı",
    tabRanking:"🏆 Sıralama",tabRules:"📋 Puanlar",
    formation:"DİZİLİŞ",selectPlayer:"KADRO",teamFull:"İlk 11 dolu!",
    alreadyIn:"Zaten ilk 11'de!",positionFull:"Pozisyon dolu!",
    added:"ilk 11'e eklendi ✓",removed:"ilk 11'den çıkarıldı",
    marketTitle:"TRANSFER PİYASASI",marketSub:"30 oyuncu — Kapalı Teklif",
    blindNotice:"🔒 Kimse teklifinizi görmez. En yüksek teklif kazanır.",
    bidPlaceholder:"Teklif (Milyon €)",submitBid:"Teklif Ver",
    bidDone:"✓ Teklif Verildi",bidResult:"Sonuç açıklanacak",
    refresh:"Yenile",invalidBid:"Geçerli teklif girin!",
    bidPlaced:"Teklifiniz verildi!",noBudgetBid:"Yeterli bütçe yok!",
    liveTitle:"CANLI MAÇ",liveSub:"Süper Lig — Gerçek Veriler",
    myMatchPts:"MAÇ PUANIN",myPlayers:"aktif oyuncu",
    eventsTitle:"OLAYLAR",startBtn:"▶ Başlat",pauseBtn:"⏸ Duraklat",
    restartBtn:"🔄 Tekrar",resetBtn:"↺ Sıfırla",
    noEvents:"Başlatmak için Başlat'a tıkla",myPlayer:"★ Senin oyuncun",
    rankTitle:"SIRALAMA",rankSub:"2024/25 Sezonu",
    weekCol:"HAFTA",seasonCol:"SEZON",managerCol:"MENAJER",
    rulesTitle:"PUAN SİSTEMİ",rulesSub:"Gerçek maç verilerine göre",
    langTitle:"DİL SEÇİN",all:"Tümü",
    assignedSquad:"KADRON (15)",squadNote:"Eklemek için dokun",
    tierStar:"⭐ Yıldız",tierStarter:"Starter",tierRotation:"Rotasyon",tierBench:"Yedek",
    posGK:"KL",posDEF:"DEF",posMF:"ORT",posFW:"FRV",
    sortVal:"Değer",sortForm:"Form",sortName:"İsim",
    searchPlayer:"Ara...",filterClub:"Kulüp",
    sellToMarket:"Piyasa değerine sat",sellToManagers:"Menajerelere sat",
    listForSale:"Satışa çıkar",listPrice:"Fiyat (Milyon €)",confirmSell:"Sat",
    cancelSell:"İptal",soldNotif:"satıldı!",listedNotif:"piyasaya çıkarıldı!",
    alreadyListed:"Zaten satışta!",myListings:"AKTİF TEKLİFLERİM",
    noListings:"Aktif teklif yok",sellMode:"💸",listedTag:"Satışta",listedFor:"Fiyat",
    mwInfo:"Piyasa değeri alım/satıma göre her gün değişir",
    mwChange:"Değer Değişimi",mwUp:"↑ artıyor",mwDown:"↓ düşüyor",mwStable:"→ sabit",
  },
};

const CLUB_COLORS={
  "Galatasaray":"#e8000d","Fenerbahçe":"#f5c518","Beşiktaş":"#d0d0d0",
  "Trabzonspor":"#7b2d8b","Başakşehir":"#ff6600","Sivasspor":"#e63946",
  "Kayserispor":"#f4a261","Alanyaspor":"#00b4d8","Antalyaspor":"#ef233c",
  "Konyaspor":"#2d6a4f","Gaziantep":"#f77f00","Kasımpaşa":"#e9c46a",
};

const INITIAL_POOL = [
  // ─── GALATASARAY ───
  {id:1,  name:"Muslera",           club:"Galatasaray", pos:"GK",  value:7.5,  form:7.1, tier:"starter"},
  {id:2,  name:"İnanç Taşdemir",    club:"Galatasaray", pos:"GK",  value:0.8,  form:4.0, tier:"bench"},
  {id:3,  name:"Güntekin Onay",     club:"Galatasaray", pos:"GK",  value:0.3,  form:3.5, tier:"bench"},
  {id:4,  name:"Bardakcı",          club:"Galatasaray", pos:"DEF", value:14.0, form:7.8, tier:"starter"},
  {id:5,  name:"Szalai",            club:"Galatasaray", pos:"DEF", value:12.5, form:7.6, tier:"starter"},
  {id:6,  name:"Boey",              club:"Galatasaray", pos:"DEF", value:11.0, form:7.3, tier:"starter"},
  {id:7,  name:"Saracchi",          club:"Galatasaray", pos:"DEF", value:9.5,  form:7.0, tier:"rotation"},
  {id:8,  name:"Abdülkerim B.",     club:"Galatasaray", pos:"DEF", value:5.0,  form:6.0, tier:"rotation"},
  {id:9,  name:"Kılınç",            club:"Galatasaray", pos:"DEF", value:1.2,  form:4.8, tier:"bench"},
  {id:10, name:"Baran Çelik",       club:"Galatasaray", pos:"DEF", value:0.4,  form:3.6, tier:"bench"},
  {id:11, name:"Torreira",          club:"Galatasaray", pos:"MF",  value:18.0, form:8.1, tier:"starter"},
  {id:12, name:"Kerem Aktürkoğlu",  club:"Galatasaray", pos:"MF",  value:22.0, form:8.4, tier:"star"},
  {id:13, name:"Dries Mertens",     club:"Galatasaray", pos:"MF",  value:16.0, form:7.9, tier:"starter"},
  {id:14, name:"Yunus Akgün",       club:"Galatasaray", pos:"MF",  value:8.0,  form:7.0, tier:"rotation"},
  {id:15, name:"Kaan Ayhan",        club:"Galatasaray", pos:"MF",  value:6.0,  form:6.5, tier:"rotation"},
  {id:16, name:"Milic",             club:"Galatasaray", pos:"MF",  value:4.5,  form:6.2, tier:"rotation"},
  {id:17, name:"Yılmaz Y.",         club:"Galatasaray", pos:"MF",  value:1.5,  form:5.0, tier:"bench"},
  {id:18, name:"Serhat Yeşilyurt",  club:"Galatasaray", pos:"MF",  value:0.3,  form:3.4, tier:"bench"},
  {id:19, name:"Osimhen",           club:"Galatasaray", pos:"FW",  value:38.0, form:9.1, tier:"star"},
  {id:20, name:"Icardi",            club:"Galatasaray", pos:"FW",  value:28.0, form:8.8, tier:"star"},
  {id:21, name:"Ziyech",            club:"Galatasaray", pos:"FW",  value:9.0,  form:7.2, tier:"rotation"},
  {id:22, name:"Seferović",         club:"Galatasaray", pos:"FW",  value:1.5,  form:5.0, tier:"bench"},
  {id:23, name:"Oliveira",          club:"Galatasaray", pos:"FW",  value:0.4,  form:3.7, tier:"bench"},
  // ─── FENERBAHÇE ───
  {id:24, name:"Livakovic",         club:"Fenerbahçe",  pos:"GK",  value:10.0, form:7.9, tier:"starter"},
  {id:25, name:"İrfan C. Eğribayat",club:"Fenerbahçe",  pos:"GK",  value:3.5,  form:6.2, tier:"rotation"},
  {id:26, name:"Ertuğrul Çelik",    club:"Fenerbahçe",  pos:"GK",  value:0.4,  form:3.4, tier:"bench"},
  {id:27, name:"Djiku",             club:"Fenerbahçe",  pos:"DEF", value:13.0, form:7.3, tier:"starter"},
  {id:28, name:"Osayi-Sam",         club:"Fenerbahçe",  pos:"DEF", value:12.5, form:7.5, tier:"starter"},
  {id:29, name:"Kadıoğlu",          club:"Fenerbahçe",  pos:"DEF", value:14.0, form:7.8, tier:"star"},
  {id:30, name:"Çağlar Söyüncü",    club:"Fenerbahçe",  pos:"DEF", value:8.5,  form:7.1, tier:"rotation"},
  {id:31, name:"Oosterwolde",       club:"Fenerbahçe",  pos:"DEF", value:7.0,  form:6.8, tier:"rotation"},
  {id:32, name:"Mert Müldür",       club:"Fenerbahçe",  pos:"DEF", value:4.0,  form:6.0, tier:"rotation"},
  {id:33, name:"Arao",              club:"Fenerbahçe",  pos:"DEF", value:1.5,  form:5.2, tier:"bench"},
  {id:34, name:"Yusuf Akçiçek",     club:"Fenerbahçe",  pos:"DEF", value:0.5,  form:3.8, tier:"bench"},
  {id:35, name:"Fred",              club:"Fenerbahçe",  pos:"MF",  value:17.0, form:7.9, tier:"starter"},
  {id:36, name:"Talisca",           club:"Fenerbahçe",  pos:"MF",  value:20.5, form:8.3, tier:"star"},
  {id:37, name:"İrfan Can Kahveci", club:"Fenerbahçe",  pos:"MF",  value:16.0, form:7.7, tier:"starter"},
  {id:38, name:"Szymanski",         club:"Fenerbahçe",  pos:"MF",  value:13.0, form:7.6, tier:"rotation"},
  {id:39, name:"Cengiz Ünder",      club:"Fenerbahçe",  pos:"MF",  value:11.5, form:7.5, tier:"rotation"},
  {id:40, name:"Pelkas",            club:"Fenerbahçe",  pos:"MF",  value:2.0,  form:5.3, tier:"bench"},
  {id:41, name:"Emre Mor",          club:"Fenerbahçe",  pos:"MF",  value:3.0,  form:5.5, tier:"bench"},
  {id:42, name:"Serdar Dursun",     club:"Fenerbahçe",  pos:"MF",  value:0.9,  form:4.2, tier:"bench"},
  {id:43, name:"Dzeko",             club:"Fenerbahçe",  pos:"FW",  value:24.0, form:8.2, tier:"star"},
  {id:44, name:"John Duran",        club:"Fenerbahçe",  pos:"FW",  value:28.0, form:8.5, tier:"star"},
  {id:45, name:"Cenk Tosun",        club:"Fenerbahçe",  pos:"FW",  value:3.5,  form:5.8, tier:"bench"},
  {id:46, name:"Rodrigo B.",        club:"Fenerbahçe",  pos:"FW",  value:0.8,  form:4.0, tier:"bench"},
  // ─── BEŞİKTAŞ ───
  {id:47, name:"Mert Günok",        club:"Beşiktaş",    pos:"GK",  value:7.5,  form:6.8, tier:"starter"},
  {id:48, name:"Destanoğlu",        club:"Beşiktaş",    pos:"GK",  value:3.5,  form:6.2, tier:"rotation"},
  {id:49, name:"Taşkın Y.",         club:"Beşiktaş",    pos:"GK",  value:0.3,  form:3.4, tier:"bench"},
  {id:50, name:"Rodrigues",         club:"Beşiktaş",    pos:"DEF", value:10.5, form:6.9, tier:"starter"},
  {id:51, name:"Ertuğrul Çetin",    club:"Beşiktaş",    pos:"DEF", value:9.0,  form:6.7, tier:"starter"},
  {id:52, name:"Rafa Silva",        club:"Beşiktaş",    pos:"DEF", value:8.5,  form:6.8, tier:"rotation"},
  {id:53, name:"Emre Demir",        club:"Beşiktaş",    pos:"DEF", value:4.5,  form:6.0, tier:"rotation"},
  {id:54, name:"Necip Uysal",       club:"Beşiktaş",    pos:"DEF", value:2.0,  form:5.0, tier:"bench"},
  {id:55, name:"Tayyip S.",         club:"Beşiktaş",    pos:"DEF", value:1.0,  form:4.5, tier:"bench"},
  {id:56, name:"Al-Musrati",        club:"Beşiktaş",    pos:"MF",  value:14.5, form:7.4, tier:"starter"},
  {id:57, name:"Oxlade-Chamberlain",club:"Beşiktaş",    pos:"MF",  value:10.0, form:7.2, tier:"rotation"},
  {id:58, name:"Gedson Fernandes",  club:"Beşiktaş",    pos:"MF",  value:9.0,  form:7.0, tier:"rotation"},
  {id:59, name:"Salih Uçan",        club:"Beşiktaş",    pos:"MF",  value:2.2,  form:5.1, tier:"bench"},
  {id:60, name:"Can Bozdoğan",      club:"Beşiktaş",    pos:"MF",  value:0.8,  form:3.9, tier:"bench"},
  {id:61, name:"Ciro Immobile",     club:"Beşiktaş",    pos:"FW",  value:21.0, form:7.8, tier:"star"},
  {id:62, name:"Batshuayi",         club:"Beşiktaş",    pos:"FW",  value:19.0, form:7.6, tier:"starter"},
  {id:63, name:"Ernest Muçi",       club:"Beşiktaş",    pos:"FW",  value:5.5,  form:6.4, tier:"rotation"},
  {id:64, name:"Semih K.",          club:"Beşiktaş",    pos:"FW",  value:1.0,  form:4.5, tier:"bench"},
  // ─── TRABZONSPOR ───
  {id:65, name:"Uğurcan Çakır",     club:"Trabzonspor", pos:"GK",  value:9.5,  form:7.2, tier:"starter"},
  {id:66, name:"Volkan B.",         club:"Trabzonspor", pos:"GK",  value:1.0,  form:4.2, tier:"bench"},
  {id:67, name:"Hüseyin A.",        club:"Trabzonspor", pos:"GK",  value:0.3,  form:3.3, tier:"bench"},
  {id:68, name:"Mads Pedersen",     club:"Trabzonspor", pos:"DEF", value:10.0, form:7.0, tier:"starter"},
  {id:69, name:"Vitor Hugo",        club:"Trabzonspor", pos:"DEF", value:5.5,  form:6.5, tier:"rotation"},
  {id:70, name:"Berat Özdemir",     club:"Trabzonspor", pos:"DEF", value:4.0,  form:6.0, tier:"rotation"},
  {id:71, name:"Stefano Denswil",   club:"Trabzonspor", pos:"DEF", value:2.5,  form:5.3, tier:"bench"},
  {id:72, name:"Ahmet Gürcan",      club:"Trabzonspor", pos:"DEF", value:0.4,  form:3.6, tier:"bench"},
  {id:73, name:"Trezeguet",         club:"Trabzonspor", pos:"MF",  value:13.5, form:7.1, tier:"starter"},
  {id:74, name:"Yusuf Yazıcı",      club:"Trabzonspor", pos:"MF",  value:11.0, form:7.2, tier:"starter"},
  {id:75, name:"Marek Hamsik",      club:"Trabzonspor", pos:"MF",  value:5.0,  form:6.0, tier:"rotation"},
  {id:76, name:"Edin Višća",        club:"Trabzonspor", pos:"MF",  value:8.0,  form:6.8, tier:"rotation"},
  {id:77, name:"Ozan İpek",         club:"Trabzonspor", pos:"MF",  value:1.0,  form:4.5, tier:"bench"},
  {id:78, name:"Visca",             club:"Trabzonspor", pos:"FW",  value:15.5, form:7.3, tier:"starter"},
  {id:79, name:"Paul Onuachu",      club:"Trabzonspor", pos:"FW",  value:9.0,  form:7.0, tier:"rotation"},
  {id:80, name:"Bakasetas",         club:"Trabzonspor", pos:"FW",  value:6.5,  form:6.6, tier:"rotation"},
  {id:81, name:"Muhammed Cham",     club:"Trabzonspor", pos:"FW",  value:1.0,  form:4.5, tier:"bench"},
  // ─── BAŞAKŞEHİR ───
  {id:82, name:"Mert Yıldırım",     club:"Başakşehir",  pos:"GK",  value:4.0,  form:6.5, tier:"starter"},
  {id:83, name:"Volkan Babacan",    club:"Başakşehir",  pos:"GK",  value:1.0,  form:4.8, tier:"bench"},
  {id:84, name:"Rafael",            club:"Başakşehir",  pos:"DEF", value:5.5,  form:6.4, tier:"rotation"},
  {id:85, name:"Mahmut Tekdemir",   club:"Başakşehir",  pos:"DEF", value:3.5,  form:5.8, tier:"rotation"},
  {id:86, name:"Junior Caiçara",    club:"Başakşehir",  pos:"DEF", value:4.5,  form:6.1, tier:"rotation"},
  {id:87, name:"Attamah",           club:"Başakşehir",  pos:"DEF", value:1.5,  form:4.8, tier:"bench"},
  {id:88, name:"Enis Destan",       club:"Başakşehir",  pos:"MF",  value:11.0, form:7.0, tier:"starter"},
  {id:89, name:"Deniz Türüç",       club:"Başakşehir",  pos:"MF",  value:6.5,  form:6.5, tier:"rotation"},
  {id:90, name:"İrfan C. Başakşehir",club:"Başakşehir", pos:"MF",  value:2.5,  form:5.2, tier:"bench"},
  {id:91, name:"Crivelli",          club:"Başakşehir",  pos:"FW",  value:8.0,  form:6.8, tier:"rotation"},
  {id:92, name:"Güven Yalçın",      club:"Başakşehir",  pos:"FW",  value:7.5,  form:6.8, tier:"rotation"},
  {id:93, name:"Youssouf Ndoye",    club:"Başakşehir",  pos:"FW",  value:1.2,  form:4.7, tier:"bench"},
  // ─── SİVASSPOR ───
  {id:94, name:"Samadov",           club:"Sivasspor",   pos:"GK",  value:3.5,  form:6.2, tier:"starter"},
  {id:95, name:"Özgür Çek",         club:"Sivasspor",   pos:"GK",  value:0.5,  form:3.7, tier:"bench"},
  {id:96, name:"Caner Osmanpaşa",   club:"Sivasspor",   pos:"DEF", value:4.0,  form:6.0, tier:"rotation"},
  {id:97, name:"Goutas",            club:"Sivasspor",   pos:"DEF", value:5.0,  form:6.3, tier:"starter"},
  {id:98, name:"Ziya Erdal",        club:"Sivasspor",   pos:"DEF", value:2.5,  form:5.3, tier:"rotation"},
  {id:99, name:"Fatih Aksoy",       club:"Sivasspor",   pos:"DEF", value:0.7,  form:4.0, tier:"bench"},
  {id:100,name:"Mert Doğan",        club:"Sivasspor",   pos:"MF",  value:6.5,  form:6.5, tier:"starter"},
  {id:101,name:"Emre Kılınç",       club:"Sivasspor",   pos:"MF",  value:8.0,  form:6.8, tier:"starter"},
  {id:102,name:"Yatabaré",          club:"Sivasspor",   pos:"MF",  value:1.5,  form:4.9, tier:"bench"},
  {id:103,name:"Erdoğan Y.",        club:"Sivasspor",   pos:"MF",  value:0.6,  form:3.8, tier:"bench"},
  {id:104,name:"Jorquera",          club:"Sivasspor",   pos:"FW",  value:7.0,  form:6.7, tier:"rotation"},
  {id:105,name:"Mostafa Mohamed",   club:"Sivasspor",   pos:"FW",  value:6.5,  form:6.5, tier:"rotation"},
  {id:106,name:"Koçak",             club:"Sivasspor",   pos:"FW",  value:0.7,  form:3.9, tier:"bench"},
  // ─── KAYSERİSPOR ───
  {id:107,name:"Caner Şen",         club:"Kayserispor", pos:"GK",  value:3.0,  form:6.0, tier:"starter"},
  {id:108,name:"Hakan Şimşek",      club:"Kayserispor", pos:"GK",  value:0.6,  form:3.7, tier:"bench"},
  {id:109,name:"Malaury Martin",    club:"Kayserispor", pos:"DEF", value:4.5,  form:6.1, tier:"rotation"},
  {id:110,name:"Recep Niyaz",       club:"Kayserispor", pos:"DEF", value:3.5,  form:5.8, tier:"rotation"},
  {id:111,name:"Nathan",            club:"Kayserispor", pos:"DEF", value:3.0,  form:5.6, tier:"rotation"},
  {id:112,name:"Furkan Soyalp",     club:"Kayserispor", pos:"DEF", value:0.8,  form:4.0, tier:"bench"},
  {id:113,name:"Musa Doğan",        club:"Kayserispor", pos:"MF",  value:5.5,  form:6.3, tier:"starter"},
  {id:114,name:"Pedro Henrique",    club:"Kayserispor", pos:"MF",  value:7.0,  form:6.7, tier:"starter"},
  {id:115,name:"Hasan Kılıç",       club:"Kayserispor", pos:"MF",  value:0.7,  form:3.8, tier:"bench"},
  {id:116,name:"Ilkay Durmuş",      club:"Kayserispor", pos:"MF",  value:0.5,  form:3.6, tier:"bench"},
  {id:117,name:"Mbaye Diagne",      club:"Kayserispor", pos:"FW",  value:8.5,  form:6.9, tier:"starter"},
  {id:118,name:"Tiago Pinto",       club:"Kayserispor", pos:"FW",  value:6.0,  form:6.4, tier:"rotation"},
  {id:119,name:"Osei",              club:"Kayserispor", pos:"FW",  value:0.8,  form:4.0, tier:"bench"},
  // ─── ALANYASPOR ───
  {id:120,name:"Runarsson",         club:"Alanyaspor",  pos:"GK",  value:4.0,  form:6.3, tier:"starter"},
  {id:121,name:"Haydar Yılmaz",     club:"Alanyaspor",  pos:"GK",  value:0.5,  form:3.6, tier:"bench"},
  {id:122,name:"Welinton",          club:"Alanyaspor",  pos:"DEF", value:5.0,  form:6.2, tier:"rotation"},
  {id:123,name:"Barreca",           club:"Alanyaspor",  pos:"DEF", value:3.5,  form:5.7, tier:"rotation"},
  {id:124,name:"Ahmet Çalık",       club:"Alanyaspor",  pos:"DEF", value:2.5,  form:5.3, tier:"rotation"},
  {id:125,name:"Alpaslan Ö.",       club:"Alanyaspor",  pos:"DEF", value:0.6,  form:3.7, tier:"bench"},
  {id:126,name:"Ceyhun Atan",       club:"Alanyaspor",  pos:"MF",  value:5.0,  form:6.2, tier:"rotation"},
  {id:127,name:"Naldo",             club:"Alanyaspor",  pos:"MF",  value:6.5,  form:6.5, tier:"starter"},
  {id:128,name:"Emre Akbaba",       club:"Alanyaspor",  pos:"MF",  value:3.0,  form:5.5, tier:"rotation"},
  {id:129,name:"Ndiaye",            club:"Alanyaspor",  pos:"MF",  value:0.7,  form:3.9, tier:"bench"},
  {id:130,name:"Davidson",          club:"Alanyaspor",  pos:"FW",  value:7.0,  form:6.7, tier:"starter"},
  {id:131,name:"Papiss Cissé",      club:"Alanyaspor",  pos:"FW",  value:5.5,  form:6.3, tier:"rotation"},
  {id:132,name:"Efecan K.",         club:"Alanyaspor",  pos:"FW",  value:0.6,  form:3.8, tier:"bench"},
  // ─── ANTALYASPOR ───
  {id:133,name:"Altay Bayındır",    club:"Antalyaspor", pos:"GK",  value:6.0,  form:6.9, tier:"starter"},
  {id:134,name:"Kamil Ahmet Ç.",    club:"Antalyaspor", pos:"GK",  value:0.5,  form:3.6, tier:"bench"},
  {id:135,name:"Nazım Sangare",     club:"Antalyaspor", pos:"DEF", value:4.5,  form:6.1, tier:"rotation"},
  {id:136,name:"Fredy",             club:"Antalyaspor", pos:"DEF", value:3.5,  form:5.7, tier:"rotation"},
  {id:137,name:"Riad Bajić",        club:"Antalyaspor", pos:"DEF", value:2.5,  form:5.2, tier:"bench"},
  {id:138,name:"Samir",             club:"Antalyaspor", pos:"MF",  value:7.0,  form:6.7, tier:"starter"},
  {id:139,name:"Gökdeniz K.",       club:"Antalyaspor", pos:"MF",  value:5.5,  form:6.3, tier:"rotation"},
  {id:140,name:"Abdallah Ndour",    club:"Antalyaspor", pos:"MF",  value:0.7,  form:3.9, tier:"bench"},
  {id:141,name:"Haris Hajradinović",club:"Antalyaspor", pos:"FW",  value:8.0,  form:6.9, tier:"starter"},
  {id:142,name:"Guray Vural",       club:"Antalyaspor", pos:"FW",  value:6.0,  form:6.4, tier:"rotation"},
  {id:143,name:"Ömer F. Beyaz",     club:"Antalyaspor", pos:"FW",  value:4.5,  form:6.0, tier:"rotation"},
  {id:144,name:"Kürşat K.",         club:"Antalyaspor", pos:"FW",  value:0.6,  form:3.7, tier:"bench"},
  // ─── KONYASPOR ───
  {id:145,name:"İlhan Palut GK",    club:"Konyaspor",   pos:"GK",  value:3.0,  form:6.0, tier:"starter"},
  {id:146,name:"Faruk İ.",          club:"Konyaspor",   pos:"GK",  value:0.5,  form:3.6, tier:"bench"},
  {id:147,name:"Obinna",            club:"Konyaspor",   pos:"DEF", value:4.0,  form:6.0, tier:"rotation"},
  {id:148,name:"Wilfried Kanga",    club:"Konyaspor",   pos:"DEF", value:3.0,  form:5.5, tier:"rotation"},
  {id:149,name:"Halil Akbunar",     club:"Konyaspor",   pos:"MF",  value:6.5,  form:6.5, tier:"starter"},
  {id:150,name:"Arber Zeneli",      club:"Konyaspor",   pos:"MF",  value:5.5,  form:6.3, tier:"rotation"},
  {id:151,name:"Rachid Bouhenna",   club:"Konyaspor",   pos:"DEF", value:2.5,  form:5.0, tier:"bench"},
  {id:152,name:"Soner Y.",          club:"Konyaspor",   pos:"MF",  value:0.6,  form:3.8, tier:"bench"},
  {id:153,name:"Yunus Mallı",       club:"Konyaspor",   pos:"FW",  value:7.0,  form:6.7, tier:"starter"},
  {id:154,name:"Muammer Y.",        club:"Konyaspor",   pos:"FW",  value:4.5,  form:6.0, tier:"rotation"},
  {id:155,name:"Emre Taşdemir",     club:"Konyaspor",   pos:"FW",  value:0.7,  form:3.9, tier:"bench"},
  // ─── GAZİANTEP ───
  {id:156,name:"Gunnar Nielsen",    club:"Gaziantep",   pos:"GK",  value:4.0,  form:6.3, tier:"starter"},
  {id:157,name:"Erdem Ş.",          club:"Gaziantep",   pos:"GK",  value:0.4,  form:3.5, tier:"bench"},
  {id:158,name:"Mbaye",             club:"Gaziantep",   pos:"DEF", value:4.5,  form:6.1, tier:"rotation"},
  {id:159,name:"Lamine Gassama",    club:"Gaziantep",   pos:"DEF", value:3.5,  form:5.8, tier:"rotation"},
  {id:160,name:"Caner Erkin",       club:"Gaziantep",   pos:"DEF", value:2.5,  form:5.3, tier:"bench"},
  {id:161,name:"Patrick Twumasi",   club:"Gaziantep",   pos:"MF",  value:6.5,  form:6.5, tier:"starter"},
  {id:162,name:"Alexandru Ioniță",  club:"Gaziantep",   pos:"MF",  value:5.5,  form:6.2, tier:"rotation"},
  {id:163,name:"Aras Özbiliz",      club:"Gaziantep",   pos:"MF",  value:4.0,  form:6.0, tier:"rotation"},
  {id:164,name:"Hüseyin D.",        club:"Gaziantep",   pos:"MF",  value:0.6,  form:3.8, tier:"bench"},
  {id:165,name:"Lucas Perez",       club:"Gaziantep",   pos:"FW",  value:7.5,  form:6.8, tier:"starter"},
  {id:166,name:"Olarenwaju Kayode", club:"Gaziantep",   pos:"FW",  value:5.0,  form:6.2, tier:"rotation"},
  {id:167,name:"Muhammet D.",       club:"Gaziantep",   pos:"FW",  value:0.7,  form:3.9, tier:"bench"},
  // ─── KASIMPAŞA ───
  {id:168,name:"Hakan Arıkan",      club:"Kasımpaşa",   pos:"GK",  value:3.5,  form:6.1, tier:"starter"},
  {id:169,name:"Koray Altınay",     club:"Kasımpaşa",   pos:"GK",  value:0.5,  form:3.6, tier:"bench"},
  {id:170,name:"Gael Clichy",       club:"Kasımpaşa",   pos:"DEF", value:3.0,  form:5.5, tier:"rotation"},
  {id:171,name:"Agus",              club:"Kasımpaşa",   pos:"DEF", value:4.0,  form:6.0, tier:"rotation"},
  {id:172,name:"Fofana",            club:"Kasımpaşa",   pos:"DEF", value:2.5,  form:5.2, tier:"bench"},
  {id:173,name:"Lamine Diack",      club:"Kasımpaşa",   pos:"MF",  value:5.5,  form:6.3, tier:"starter"},
  {id:174,name:"Muhammet Demir",    club:"Kasımpaşa",   pos:"MF",  value:4.5,  form:6.0, tier:"rotation"},
  {id:175,name:"Serdar Gürler",     club:"Kasımpaşa",   pos:"MF",  value:6.5,  form:6.5, tier:"starter"},
  {id:176,name:"Ercan T.",          club:"Kasımpaşa",   pos:"MF",  value:0.6,  form:3.7, tier:"bench"},
  {id:177,name:"Mame Thiam",        club:"Kasımpaşa",   pos:"FW",  value:7.0,  form:6.7, tier:"starter"},
  {id:178,name:"Mbaye Niang",       club:"Kasımpaşa",   pos:"FW",  value:6.0,  form:6.4, tier:"rotation"},
  {id:179,name:"Enes Ü.",           club:"Kasımpaşa",   pos:"FW",  value:0.7,  form:3.9, tier:"bench"},
];

const MATCH_DATA = [
  {
    id:"m1",matchday:18,home:"Fenerbahçe",away:"Konyaspor",score:[3,0],date:"18.01.2025",
    events:[
      {min:11,player:"Talisca",      club:"Fenerbahçe",type:"tor",pts:6},
      {min:23,player:"İrfan Can Kahveci",club:"Fenerbahçe",type:"assist",pts:4},
      {min:34,player:"Dzeko",        club:"Fenerbahçe",type:"tor",pts:6},
      {min:34,player:"Talisca",      club:"Fenerbahçe",type:"assist",pts:4},
      {min:47,player:"Fred",         club:"Fenerbahçe",type:"pass",pts:0.1},
      {min:61,player:"John Duran",   club:"Fenerbahçe",type:"tor",pts:6},
      {min:61,player:"İrfan Can Kahveci",club:"Fenerbahçe",type:"assist",pts:4},
      {min:72,player:"Djiku",        club:"Fenerbahçe",type:"zweikampf",pts:0.5},
      {min:78,player:"Livakovic",    club:"Fenerbahçe",type:"clean_sheet_gk",pts:4},
      {min:88,player:"Fred",         club:"Fenerbahçe",type:"gelbe_karte",pts:-2},
    ],
  },
  {
    id:"m2",matchday:18,home:"Galatasaray",away:"Trabzonspor",score:[2,1],date:"19.01.2025",
    events:[
      {min:8, player:"Osimhen",         club:"Galatasaray",type:"tor",pts:6},
      {min:8, player:"Kerem Aktürkoğlu",club:"Galatasaray",type:"assist",pts:4},
      {min:31,player:"Trezeguet",       club:"Trabzonspor",type:"tor",pts:6},
      {min:31,player:"Visca",           club:"Trabzonspor",type:"assist",pts:4},
      {min:45,player:"Torreira",        club:"Galatasaray",type:"gelbe_karte",pts:-2},
      {min:58,player:"Icardi",          club:"Galatasaray",type:"tor",pts:6},
      {min:58,player:"Dries Mertens",   club:"Galatasaray",type:"assist",pts:4},
      {min:67,player:"Bardakcı",        club:"Galatasaray",type:"zweikampf",pts:0.5},
    ],
  },
  {
    id:"m3",matchday:17,home:"Beşiktaş",away:"Trabzonspor",score:[2,2],date:"12.01.2025",
    events:[
      {min:19,player:"Ciro Immobile",   club:"Beşiktaş",  type:"tor",pts:6},
      {min:19,player:"Batshuayi",       club:"Beşiktaş",  type:"assist",pts:4},
      {min:33,player:"Visca",           club:"Trabzonspor",type:"tor",pts:6},
      {min:44,player:"Trezeguet",       club:"Trabzonspor",type:"tor",pts:6},
      {min:55,player:"Al-Musrati",      club:"Beşiktaş",  type:"gelbe_karte",pts:-2},
      {min:71,player:"Batshuayi",       club:"Beşiktaş",  type:"tor",pts:6},
      {min:71,player:"Ciro Immobile",   club:"Beşiktaş",  type:"assist",pts:4},
      {min:85,player:"Ertuğrul Çetin",  club:"Beşiktaş",  type:"zweikampf",pts:0.5},
    ],
  },
];

const EV_DE={tor:"Tor ⚽",assist:"Assist 🎯",gelbe_karte:"Gelbe Karte 🟨",rote_karte:"Rote Karte 🟥",
  eigentor:"Eigentor 😬",clean_sheet_gk:"Clean Sheet 🧤",clean_sheet_def:"Clean Sheet 🛡",
  zweikampf:"Zweikampf 💪",schuss:"Schuss 🎯",fehlpass:"Fehlpass ❌",pass:"Pass 📤"};
const EV_TR={tor:"Gol ⚽",assist:"Asist 🎯",gelbe_karte:"Sarı Kart 🟨",rote_karte:"Kırmızı Kart 🟥",
  eigentor:"Kendi Kalesi 😬",clean_sheet_gk:"Gol Yememe 🧤",clean_sheet_def:"Gol Yememe 🛡",
  zweikampf:"İkili Mücadele 💪",schuss:"İsabetli Şut 🎯",fehlpass:"Hatalı Pas ❌",pass:"Pas 📤"};

const POINT_RULES=[
  {type:"tor",pts:"+6",c:"#10b981"},{type:"assist",pts:"+4",c:"#10b981"},
  {type:"clean_sheet_gk",pts:"+4",c:"#10b981"},{type:"clean_sheet_def",pts:"+2",c:"#10b981"},
  {type:"zweikampf",pts:"+0.5",c:"#10b981"},{type:"schuss",pts:"+1",c:"#10b981"},
  {type:"pass",pts:"+0.1",c:"#64b5f6"},{type:"fehlpass",pts:"-0.2",c:"#ef4444"},
  {type:"gelbe_karte",pts:"-2",c:"#ef4444"},{type:"rote_karte",pts:"-5",c:"#ef4444"},
  {type:"eigentor",pts:"-4",c:"#ef4444"},
];

const FORMATIONS={
  "3-5-2":{GK:1,DEF:3,MF:5,FW:2},"3-4-3":{GK:1,DEF:3,MF:4,FW:3},
  "3-6-1":{GK:1,DEF:3,MF:6,FW:1},"4-4-2":{GK:1,DEF:4,MF:4,FW:2},
  "4-2-4":{GK:1,DEF:4,MF:2,FW:4},"4-5-1":{GK:1,DEF:4,MF:5,FW:1},
  "4-3-3":{GK:1,DEF:4,MF:3,FW:3},"5-3-2":{GK:1,DEF:5,MF:3,FW:2},
  "5-4-1":{GK:1,DEF:5,MF:4,FW:1},"5-2-3":{GK:1,DEF:5,MF:2,FW:3},
};

const LEADERBOARD_BASE=[
  {name:"TrabzonFan92",pts:387,weekly:52},{name:"GalatasarayKing",pts:371,weekly:48},
  {name:"FenerBoy",pts:358,weekly:61},{name:"BeşiktaşUltra",pts:344,weekly:39},
  {name:"SüperLigMaster",pts:331,weekly:44},
];

function fmtM(v){return v>=1?`${v.toFixed(2)}M \u20ac`:`${(v*1000).toFixed(0)}K \u20ac`;}
function fmtTime(ms){
  if(ms<=0)return "—";
  const h=Math.floor(ms/3600000),m=Math.floor((ms%3600000)/60000);
  return h>0?`${h}h ${m}m`:`${m}m`;
}
function calcPts(name,matchId){
  const m=MATCH_DATA.find(x=>x.id===matchId);
  if(!m)return 0;
  return m.events.filter(e=>e.player===name).reduce((s,e)=>s+e.pts,0);
}
function calcTeamPts(team,matchId){return team.reduce((s,p)=>s+calcPts(p.name,matchId),0);}

function buildSquad(){
  const shuffle=(arr)=>[...arr].sort(()=>Math.random()-.5);
  const noStars=INITIAL_POOL.filter(p=>p.tier!=="star");
  const topClubs=["Galatasaray","Fenerbahçe","Beşiktaş"];
  function pickDiverse(pool,n){
    const sh=shuffle(pool);
    const picked=[];const topCount={};
    for(const p of sh){
      if(picked.length>=n)break;
      if(topClubs.includes(p.club)){
        if((topCount[p.club]||0)>=1)continue;
        topCount[p.club]=(topCount[p.club]||0)+1;
      }
      picked.push(p);
    }
    if(picked.length<n){
      const used=new Set(picked.map(p=>p.id));
      for(const p of sh){if(picked.length>=n)break;if(!used.has(p.id))picked.push(p);}
    }
    return picked;
  }
  const starters=noStars.filter(p=>p.tier==="starter");
  const rotations=noStars.filter(p=>p.tier==="rotation");
  const benches=noStars.filter(p=>p.tier==="bench");
  const sel3=pickDiverse(starters,3);
  const used3=new Set(sel3.map(p=>p.id));
  const sel6r=pickDiverse(rotations.filter(p=>!used3.has(p.id)),6);
  const used9=new Set([...sel3,...sel6r].map(p=>p.id));
  const sel6b=pickDiverse(benches.filter(p=>!used9.has(p.id)),6);
  const squad=[...sel3,...sel6r,...sel6b].slice(0,15);
  const total=squad.reduce((s,p)=>s+p.value,0)||1;
  const factor=45/total;
  return squad.map(p=>({...p,value:Math.round(p.value*factor*100)/100,baseValue:p.value*factor,squadTier:p.tier}));
}

function generateMarket(excludeIds){
  return INITIAL_POOL
    .filter(p=>!excludeIds.includes(p.id))
    .sort(()=>Math.random()-.5)
    .slice(0,30)
    .map(p=>({...p,marketId:Math.random().toString(36).substr(2,9),
      expiresAt:Date.now()+(Math.floor(Math.random()*24)+5)*3600*1000,
      myBid:null,submitted:false}));
}

function PosBadge({pos,t}){
  const C={GK:"#f59e0b",DEF:"#3b82f6",MF:"#10b981",FW:"#ef4444"};
  const L={GK:t.posGK,DEF:t.posDEF,MF:t.posMF,FW:t.posFW};
  return <span style={{background:C[pos],color:"#fff",fontSize:9,fontWeight:700,
    padding:"2px 5px",borderRadius:3,flexShrink:0}}>{L[pos]}</span>;
}
function TierBadge({tier,t}){
  const m={star:{c:"#b45309",l:t.tierStar},starter:{c:"#1e40af",l:t.tierStarter},
    rotation:{c:"#374151",l:t.tierRotation},bench:{c:"#111827",l:t.tierBench}};
  const d=m[tier]||m.bench;
  return <span style={{background:d.c,color:"#fff",fontSize:8,fontWeight:700,
    padding:"1px 5px",borderRadius:3,flexShrink:0}}>{d.l}</span>;
}
function ClubDot({club}){
  return <span style={{display:"inline-block",width:7,height:7,borderRadius:"50%",
    background:CLUB_COLORS[club]||"#555",marginRight:4,flexShrink:0}}/>;
}
function Notif({msg,type}){
  return <div style={{position:"fixed",top:20,right:16,zIndex:9999,
    background:type==="error"?"#ef4444":"#10b981",color:"#fff",padding:"11px 18px",
    borderRadius:10,fontWeight:700,fontSize:13,boxShadow:"0 6px 24px rgba(0,0,0,.5)",
    animation:"popIn .25s ease"}}>{msg}</div>;
}
function ValueDelta({pct}){
  if(!pct||pct===0)return <span style={{fontSize:10,color:"#555"}}>0%</span>;
  return <span style={{fontSize:10,color:pct>0?"#10b981":"#ef4444",fontWeight:700}}>
    {pct>0?"↑":"↓"}{Math.abs(pct*100).toFixed(1)}%
  </span>;
}

function LangScreen({onSelect}){
  return(
    <div style={{position:"fixed",inset:0,background:"#06060f",
      display:"flex",alignItems:"center",justifyContent:"center"}}>
      <style>{"@keyframes fadeUp{from{opacity:0;transform:translateY(24px)}to{opacity:1;transform:translateY(0)}}"}</style>
      <div style={{textAlign:"center",animation:"fadeUp .6s ease",padding:"0 32px"}}>
        <div style={{fontFamily:"Anton,sans-serif",fontSize:48,letterSpacing:3,color:"#fff",lineHeight:.95}}>SÜPER LİG</div>
        <div style={{fontFamily:"Anton,sans-serif",fontSize:48,letterSpacing:3,color:"#c8102e",lineHeight:.95,marginBottom:8}}>FANTASY</div>
        <div style={{width:50,height:3,background:"#c8102e",margin:"14px auto 28px",borderRadius:2}}/>
        <p style={{color:"#666",fontSize:13,letterSpacing:2,marginBottom:36}}>FANTASY MANAGER</p>
        <div style={{display:"flex",gap:16,justifyContent:"center"}}>
          {[{code:"de",label:"🇩🇪 Deutsch"},{code:"tr",label:"🇹🇷 Türkçe"}].map(l=>(
            <button key={l.code} onClick={()=>onSelect(l.code)} style={{
              background:"transparent",border:"2px solid #333",color:"#fff",
              padding:"16px 36px",borderRadius:12,cursor:"pointer",
              fontFamily:"Anton,sans-serif",fontSize:18,letterSpacing:1}}>
              {l.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function App(){
  const [lang,setLang]=useState(null);
  if(!lang)return <LangScreen onSelect={setLang}/>;
  return <Game lang={lang} onChangeLang={()=>setLang(null)}/>;
}

function Game({lang,onChangeLang}){
  const [tab,setTab]=useState("team");
  const [formation,setFormation]=useState("4-3-3");
  const [squad]=useState(()=>buildSquad());
  const [players,setPlayers]=useState(()=>{
    const b={};INITIAL_POOL.forEach(p=>{b[p.id]=p.value;});return b;
  });
  const [transactions,setTransactions]=useState([]);
  const [currentDay]=useState(()=>Math.floor(Date.now()/86400000));
  const [xi,setXi]=useState([]);
  const [transferBudget,setTransferBudget]=useState(20);
  const [market,setMarket]=useState(null);
  const [bidInputs,setBidInputs]=useState({});
  const [now,setNow]=useState(Date.now());
  const [notif,setNotif]=useState(null);
  const [activeMatch,setActiveMatch]=useState("m1");
  const [liveMin,setLiveMin]=useState(0);
  const [liveRunning,setLiveRunning]=useState(false);
  const [shownEvents,setShownEvents]=useState([]);
  const [posFilter,setPosFilter]=useState("ALL");
  const [searchQ,setSearchQ]=useState("");
  const [sortKey,setSortKey]=useState("value");
  const [marketSearch,setMarketSearch]=useState("");
  const [marketClub,setMarketClub]=useState("ALL");
  const [myListings,setMyListings]=useState([]);
  const [soldIds,setSoldIds]=useState(new Set());
  const [sellModal,setSellModal]=useState(null);
  const [listPriceInput,setListPriceInput]=useState("");
  const [marketTab,setMarketTab]=useState("buy");

  useEffect(()=>{
    if(lang&&!market)setMarket(generateMarket(squad.map(p=>p.id)));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  },[lang]);

  useEffect(()=>{
    const tick=setInterval(()=>setNow(Date.now()),30000);
    return()=>clearInterval(tick);
  },[]);

  useEffect(()=>{
    if(!liveRunning)return;
    if(liveMin>=90){setLiveRunning(false);return;}
    const match=MATCH_DATA.find(m=>m.id===activeMatch);
    const timer=setTimeout(()=>{
      setLiveMin(m=>{
        const next=m+1;
        const ev=match?.events.find(e=>e.min===next);
        if(ev)setShownEvents(p=>[ev,...p]);
        return next;
      });
    },180);
    return()=>clearTimeout(timer);
  },[liveRunning,liveMin,activeMatch]);

  const t=T[lang];
  const evLabels=lang==="tr"?EV_TR:EV_DE;
  const notify=(msg,type="success")=>{setNotif({msg,type});setTimeout(()=>setNotif(null),2800);};

  const squadWithValues=squad.filter(p=>!soldIds.has(p.id)).map(p=>({...p,value:players[p.id]??p.value}));
  const inXI=id=>xi.some(p=>p.id===id);
  const formReq=FORMATIONS[formation];
  const xiByPos={GK:[],DEF:[],MF:[],FW:[]};
  xi.forEach(p=>xiByPos[p.pos]?.push(p));

  const addToXI=p=>{
    if(inXI(p.id)){notify(t.alreadyIn,"error");return;}
    if(xi.length>=11){notify(t.teamFull,"error");return;}
    if((xiByPos[p.pos]?.length||0)>=formReq[p.pos]){notify(t.positionFull,"error");return;}
    setXi(prev=>[...prev,{...p,value:players[p.id]??p.value}]);
    notify(`${p.name} ${t.added}`);
  };
  const removeFromXI=id=>{
    const p=xi.find(x=>x.id===id);
    if(!p)return;
    setXi(prev=>prev.filter(x=>x.id!==id));
    notify(`${p.name} ${t.removed}`);
  };

  const submitBid=listing=>{
    const val=parseFloat(bidInputs[listing.marketId]);
    if(!val||val<=0){notify(t.invalidBid,"error");return;}
    if(val>transferBudget){notify(t.noBudgetBid,"error");return;}
    setTransactions(prev=>[...prev,{playerId:listing.id,type:"buy",day:currentDay}]);
    setMarket(prev=>prev.map(l=>l.marketId===listing.marketId?{...l,myBid:val,submitted:true}:l));
    setBidInputs(p=>({...p,[listing.marketId]:""}));
    notify(t.bidPlaced);
  };

  const sellToMarket=p=>{
    const val=players[p.id]??p.value;
    setTransactions(prev=>[...prev,{playerId:p.id,type:"sell",day:currentDay}]);
    setTransferBudget(b=>Math.round((b+val)*100)/100);
    setXi(prev=>prev.filter(x=>x.id!==p.id));
    setSoldIds(prev=>new Set([...prev,p.id]));
    setSellModal(null);
    notify(`${p.name} ${t.soldNotif} +${fmtM(val)}`);
  };

  const listForSale=p=>{
    const price=parseFloat(listPriceInput);
    if(!price||price<=0){notify(t.invalidBid,"error");return;}
    if(myListings.some(l=>l.id===p.id)){notify(t.alreadyListed,"error");return;}
    const listing={...p,value:players[p.id]??p.value,
      marketId:Math.random().toString(36).substr(2,9),askPrice:price,
      expiresAt:Date.now()+(Math.floor(Math.random()*20)+5)*3600*1000,
      myBid:null,submitted:false,isMyListing:true};
    setMyListings(prev=>[...prev,listing]);
    setMarket(prev=>[listing,...(prev||[])]);
    setSellModal(null);setListPriceInput("");
    notify(`${p.name} ${t.listedNotif}`);
  };

  const myMatchPts=calcTeamPts(xi,activeMatch);
  const mySeasonPts=MATCH_DATA.reduce((s,m)=>s+calcTeamPts(xi,m.id),0);
  const myLivePts=shownEvents.reduce((s,e)=>xi.some(p=>p.name===e.player)?s+e.pts:s,0);
  const currentMatch=MATCH_DATA.find(m=>m.id===activeMatch);
  const lb=[...LEADERBOARD_BASE,{name:lang==="tr"?"Sen":"Du",pts:mySeasonPts,weekly:myMatchPts,isMe:true}]
    .sort((a,b)=>b.pts-a.pts);

  const filteredSquad=useMemo(()=>{
    let s=squadWithValues;
    if(posFilter!=="ALL")s=s.filter(p=>p.pos===posFilter);
    if(searchQ)s=s.filter(p=>p.name.toLowerCase().includes(searchQ.toLowerCase()));
    s=[...s].sort((a,b)=>sortKey==="value"?b.value-a.value:sortKey==="form"?b.form-a.form:a.name.localeCompare(b.name));
    return s;
  },[squadWithValues,posFilter,searchQ,sortKey]);

  const filteredMarket=useMemo(()=>{
    if(!market)return[];
    let m=market.map(p=>({...p,value:players[p.id]??p.value}));
    if(marketSearch)m=m.filter(p=>p.name.toLowerCase().includes(marketSearch.toLowerCase())||p.club.toLowerCase().includes(marketSearch.toLowerCase()));
    if(marketClub!=="ALL")m=m.filter(p=>p.club===marketClub);
    return m;
  },[market,players,marketSearch,marketClub]);

  const allClubs=[...new Set(INITIAL_POOL.map(p=>p.club))].sort();
  const posOrder=["GK","DEF","MF","FW"];
  const posColors={GK:"#f59e0b",DEF:"#3b82f6",MF:"#10b981",FW:"#ef4444"};

  const TABS=[
    {k:"team",label:t.tabTeam},{k:"market",label:t.tabMarket},
    {k:"live",label:t.tabLive},{k:"ranking",label:t.tabRanking},{k:"rules",label:t.tabRules},
  ];

  return(
    <div style={{fontFamily:"DM Sans,sans-serif",background:"#06060f",
      position:"fixed",inset:0,display:"flex",flexDirection:"column",
      overflow:"hidden",color:"#e8e8f0"}}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&family=Anton&display=swap" rel="stylesheet"/>
      <style>{`
        *{box-sizing:border-box;margin:0;padding:0;}
        html,body{overflow:hidden;height:100%;width:100%;}
        input{color:#e8e8f0;outline:none;}
        ::-webkit-scrollbar{width:3px;}
        ::-webkit-scrollbar-thumb{background:#c8102e;border-radius:2px;}
        @keyframes popIn{from{opacity:0;transform:scale(.85)}to{opacity:1;transform:scale(1)}}
        @keyframes fadeUp{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
        @keyframes fadeSlide{from{opacity:0;transform:translateX(-8px)}to{opacity:1;transform:translateX(0)}}
        .tab-btn{transition:all .15s;}
        .tab-btn.active{background:rgba(255,255,255,.95)!important;color:#c8102e!important;}
        .player-row:active{background:#1a1a2e!important;}
        .form-btn:active{background:#c8102e!important;}
        .rm-hint{opacity:0;transition:opacity .15s;}
        .pslot:hover .rm-hint,.pslot:active .rm-hint{opacity:1;}
      `}</style>

      {notif&&<Notif {...notif}/>}

      {/* SELL MODAL */}
      {sellModal&&(
        <div style={{position:"fixed",inset:0,background:"rgba(0,0,0,.8)",
          display:"flex",alignItems:"center",justifyContent:"center",zIndex:900}}
          onClick={()=>setSellModal(null)}>
          <div onClick={e=>e.stopPropagation()} style={{
            background:"#0e0e1c",border:"1px solid #c8102e44",borderRadius:16,
            padding:24,width:320,maxWidth:"90vw",boxShadow:"0 20px 60px rgba(0,0,0,.8)"}}>
            <div style={{display:"flex",gap:12,alignItems:"center",marginBottom:18}}>
              <div style={{width:48,height:48,borderRadius:10,flexShrink:0,
                background:`linear-gradient(135deg,${CLUB_COLORS[sellModal.club]||"#333"},${CLUB_COLORS[sellModal.club]||"#333"}55)`,
                display:"flex",alignItems:"center",justifyContent:"center",
                fontFamily:"Anton,sans-serif",fontSize:16,color:"#fff"}}>
                {sellModal.name.slice(0,2).toUpperCase()}
              </div>
              <div>
                <div style={{fontWeight:700,fontSize:15}}>{sellModal.name}</div>
                <div style={{fontSize:11,color:"#555",marginTop:2}}>{sellModal.club}</div>
                <div style={{fontSize:12,color:"#ffd700",marginTop:2}}>{fmtM(players[sellModal.id]??sellModal.value)}</div>
              </div>
            </div>
            <div style={{background:"#0a0a18",borderRadius:10,padding:14,marginBottom:10}}>
              <div style={{fontSize:12,fontWeight:700,marginBottom:8}}>1️⃣ {t.sellToMarket}</div>
              <button onClick={()=>sellToMarket(sellModal)} style={{
                width:"100%",background:"#c8102e",color:"#fff",border:"none",
                padding:"10px",borderRadius:8,cursor:"pointer",fontWeight:700,fontSize:13}}>
                {t.confirmSell} ({fmtM(players[sellModal.id]??sellModal.value)})
              </button>
            </div>
            <div style={{background:"#0a0a18",borderRadius:10,padding:14,marginBottom:14}}>
              <div style={{fontSize:12,fontWeight:700,marginBottom:8}}>2️⃣ {t.sellToManagers}</div>
              <div style={{display:"flex",gap:8}}>
                <input type="number" step="0.1" min="0.1" placeholder={t.listPrice}
                  value={listPriceInput} onChange={e=>setListPriceInput(e.target.value)}
                  style={{flex:1,background:"#14142a",border:"1px solid #1e1e38",
                    color:"#fff",padding:"8px 10px",borderRadius:7,fontSize:12}}/>
                <button onClick={()=>listForSale(sellModal)} style={{
                  background:"#1e40af",color:"#fff",border:"none",
                  padding:"8px 12px",borderRadius:7,cursor:"pointer",fontWeight:700,fontSize:12}}>
                  {t.listForSale}
                </button>
              </div>
            </div>
            <button onClick={()=>setSellModal(null)} style={{
              width:"100%",background:"#14142a",color:"#888",border:"none",
              padding:"9px",borderRadius:8,cursor:"pointer",fontSize:12}}>
              {t.cancelSell}
            </button>
          </div>
        </div>
      )}

      {/* HEADER */}
      <header style={{background:"linear-gradient(135deg,#be0d27,#650010)",
        borderBottom:"1px solid rgba(255,255,255,.07)",flexShrink:0}}>
        <div style={{padding:"10px 16px 0"}}>
          <div style={{display:"flex",alignItems:"center",justifyContent:"space-between"}}>
            <div style={{display:"flex",alignItems:"center",gap:10}}>
              <div style={{fontFamily:"Anton,sans-serif",fontSize:22,letterSpacing:2}}>
                SÜPER LİG <span style={{color:"#ffd700"}}>FANTASY</span>
              </div>
              <button onClick={onChangeLang} style={{background:"rgba(255,255,255,.15)",
                border:"none",color:"rgba(255,255,255,.8)",padding:"3px 9px",
                borderRadius:5,cursor:"pointer",fontSize:11,fontWeight:600}}>
                {lang==="de"?"🇩🇪 DE":"🇹🇷 TR"}
              </button>
            </div>
            <div style={{display:"flex",gap:16}}>
              <div style={{textAlign:"right"}}>
                <div style={{fontSize:9,color:"rgba(255,255,255,.45)",letterSpacing:1}}>{t.transferBudget}</div>
                <div style={{fontFamily:"Anton,sans-serif",fontSize:18,color:"#ffd700"}}>{fmtM(transferBudget)}</div>
              </div>
              <div style={{textAlign:"right"}}>
                <div style={{fontSize:9,color:"rgba(255,255,255,.45)",letterSpacing:1}}>{t.seasonPts}</div>
                <div style={{fontFamily:"Anton,sans-serif",fontSize:18,color:"#fff"}}>{mySeasonPts.toFixed(0)}</div>
              </div>
            </div>
          </div>
          <div style={{display:"flex",gap:2,marginTop:8,overflowX:"auto"}}>
            {TABS.map(tb=>(
              <button key={tb.k} onClick={()=>setTab(tb.k)}
                className={"tab-btn"+(tab===tb.k?" active":"")}
                style={{background:"rgba(255,255,255,.1)",color:"rgba(255,255,255,.85)",
                  border:"none",padding:"7px 12px",borderRadius:"6px 6px 0 0",cursor:"pointer",
                  fontWeight:700,fontSize:11,whiteSpace:"nowrap",flexShrink:0}}>
                {tb.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* CONTENT */}
      <main style={{flex:1,overflow:"hidden",display:"flex",flexDirection:"column",minHeight:0}}>
        <div style={{flex:1,overflow:"auto",padding:"10px 14px",
          WebkitOverflowScrolling:"touch",minHeight:0}}>

          {/* ══ TEAM TAB ══ */}
          {tab==="team"&&(
            <div style={{display:"flex",flexDirection:"column",gap:8,height:"100%",animation:"fadeUp .3s ease"}}>

              {/* Formation picker */}
              <div style={{background:"#0e0e1c",borderRadius:10,padding:"8px 12px",
                border:"1px solid #1a1a30",flexShrink:0}}>
                <div style={{fontSize:9,color:"#555",letterSpacing:1,marginBottom:6}}>{t.formation} — {formation}</div>
                <div style={{display:"flex",flexWrap:"wrap",gap:4}}>
                  {Object.keys(FORMATIONS).map(f=>(
                    <button key={f} className="form-btn" onClick={()=>setFormation(f)} style={{
                      background:formation===f?"#c8102e":"#1a1a2e",color:"#fff",border:"none",
                      padding:"4px 10px",borderRadius:5,cursor:"pointer",fontWeight:700,fontSize:11}}>
                      {f}
                    </button>
                  ))}
                </div>
              </div>

              {/* Pitch */}
              <div style={{
                flex:"0 0 52%",position:"relative",
                background:"linear-gradient(180deg,#0d5c0d,#0e6e0e 14%,#0d5c0d 28%,#0e6e0e 42%,#0d5c0d 56%,#0e6e0e 70%,#0d5c0d 84%,#0e6e0e)",
                borderRadius:12,border:"2px solid #1a6e1a",
                display:"flex",flexDirection:"column",overflow:"hidden",minHeight:0,
              }}>
                {/* Field lines */}
                <div style={{position:"absolute",top:"50%",left:"4%",right:"4%",height:1,
                  background:"rgba(255,255,255,.18)",zIndex:0,pointerEvents:"none"}}/>
                <div style={{position:"absolute",top:"50%",left:"50%",width:66,height:66,
                  borderRadius:"50%",border:"1px solid rgba(255,255,255,.18)",
                  transform:"translate(-50%,-50%)",zIndex:0,pointerEvents:"none"}}/>
                <div style={{position:"absolute",top:0,left:"18%",right:"18%",height:"16%",
                  border:"1px solid rgba(255,255,255,.13)",borderTop:"none",zIndex:0,pointerEvents:"none"}}/>
                <div style={{position:"absolute",bottom:0,left:"18%",right:"18%",height:"16%",
                  border:"1px solid rgba(255,255,255,.13)",borderBottom:"none",zIndex:0,pointerEvents:"none"}}/>
                {/* Score badge */}
                <div style={{position:"absolute",top:8,right:10,background:"rgba(0,0,0,.65)",
                  borderRadius:8,padding:"4px 10px",textAlign:"right",zIndex:2,pointerEvents:"none"}}>
                  <div style={{fontSize:8,color:"rgba(255,255,255,.4)"}}>PUAN</div>
                  <div style={{fontFamily:"Anton,sans-serif",fontSize:18,color:"#ffd700",lineHeight:1}}>{mySeasonPts.toFixed(0)}</div>
                </div>
                {/* Players */}
                <div style={{flex:1,display:"flex",flexDirection:"column",
                  justifyContent:"space-evenly",padding:"6px 4px",zIndex:1,position:"relative"}}>
                  {["FW","MF","DEF","GK"].map(pos=>{
                    const count=formReq[pos];
                    const avSz=count>=6?32:count>=5?36:42;
                    const gap=count>=6?2:count>=5?4:count>=4?8:14;
                    const slotW=count>=6?48:count>=5?54:62;
                    return(
                      <div key={pos} style={{display:"flex",justifyContent:"center",
                        alignItems:"center",gap,width:"100%"}}>
                        {Array.from({length:count}).map((_,i)=>{
                          const pl=xiByPos[pos][i];
                          return(
                            <div key={i} className="pslot" style={{textAlign:"center",width:slotW,flexShrink:0}}>
                              {pl?(
                                <div onClick={()=>removeFromXI(pl.id)} style={{cursor:"pointer"}}>
                                  <div style={{width:avSz,height:avSz,borderRadius:"50%",margin:"0 auto 2px",
                                    background:`linear-gradient(145deg,${CLUB_COLORS[pl.club]||"#2a2a4a"},${CLUB_COLORS[pl.club]||"#1a1a3a"}99)`,
                                    display:"flex",alignItems:"center",justifyContent:"center",
                                    fontFamily:"Anton,sans-serif",fontSize:Math.max(9,avSz/3.5|0),color:"#fff",
                                    border:`2px solid ${CLUB_COLORS[pl.club]||"rgba(255,255,255,.3)"}`,
                                    boxShadow:"0 2px 8px rgba(0,0,0,.6)",position:"relative"}}>
                                    {pl.name.slice(0,2).toUpperCase()}
                                    <div className="rm-hint" style={{position:"absolute",inset:0,
                                      borderRadius:"50%",background:"rgba(220,38,38,.88)",
                                      display:"flex",alignItems:"center",justifyContent:"center",
                                      fontSize:16,color:"#fff",fontWeight:700}}>×</div>
                                  </div>
                                  <div style={{background:"rgba(0,0,0,.7)",borderRadius:3,
                                    padding:"1px 3px",margin:"0 auto",maxWidth:slotW-2}}>
                                    <div style={{fontSize:8,fontWeight:700,color:"#fff",
                                      whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}}>
                                      {pl.name.split(" ").slice(-1)[0]}
                                    </div>
                                    <div style={{fontSize:8,color:"#ffd700",fontWeight:700}}>
                                      {calcPts(pl.name,activeMatch).toFixed(1)}p
                                    </div>
                                  </div>
                                </div>
                              ):(
                                <div>
                                  <div style={{width:avSz,height:avSz,borderRadius:"50%",margin:"0 auto 2px",
                                    border:"2px dashed rgba(255,255,255,.22)",
                                    display:"flex",alignItems:"center",justifyContent:"center",
                                    color:"rgba(255,255,255,.2)",fontSize:18}}>+</div>
                                  <div style={{fontSize:7,color:"rgba(255,255,255,.3)",textAlign:"center"}}>
                                    {{GK:t.posGK,DEF:t.posDEF,MF:t.posMF,FW:t.posFW}[pos]}
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Squad list — sorted by GK/DEF/MF/FW */}
              <div style={{flex:1,background:"#0e0e1c",borderRadius:12,
                border:"1px solid #1a1a30",display:"flex",flexDirection:"column",minHeight:0,overflow:"hidden"}}>
                <div style={{padding:"7px 10px",borderBottom:"1px solid #1a1a30",flexShrink:0,
                  display:"flex",alignItems:"center",gap:8}}>
                  <div style={{fontSize:10,color:"#c8102e",fontWeight:700}}>
                    {t.assignedSquad} — {xi.length}/11
                  </div>
                  <div style={{fontSize:10,color:"#444",marginLeft:"auto"}}>{t.squadNote}</div>
                  <input placeholder="🔍" value={searchQ} onChange={e=>setSearchQ(e.target.value)}
                    style={{background:"#14142a",border:"1px solid #1e1e38",borderRadius:5,
                      padding:"3px 7px",fontSize:11,width:70}}/>
                </div>
                <div style={{flex:1,overflowY:"auto",WebkitOverflowScrolling:"touch"}}>
                  {posOrder.map(pos=>{
                    const grouped=squadWithValues.filter(p=>p.pos===pos)
                      .filter(p=>!searchQ||p.name.toLowerCase().includes(searchQ.toLowerCase()));
                    if(grouped.length===0)return null;
                    return(
                      <div key={pos}>
                        <div style={{display:"flex",alignItems:"center",gap:6,
                          padding:"4px 10px",background:"#0a0a18",
                          borderBottom:"1px solid #1a1a30",
                          position:"sticky",top:0,zIndex:2}}>
                          <span style={{background:posColors[pos],color:"#fff",
                            fontSize:9,fontWeight:700,padding:"2px 6px",borderRadius:3}}>
                            {{GK:t.posGK,DEF:t.posDEF,MF:t.posMF,FW:t.posFW}[pos]}
                          </span>
                          <span style={{fontSize:10,color:"#555"}}>
                            {grouped.filter(p=>inXI(p.id)).length}/{grouped.length}
                          </span>
                        </div>
                        {grouped.map(p=>{
                          const already=inXI(p.id);
                          const posFull=(xiByPos[pos]?.length||0)>=formReq[pos];
                          const disabled=already||posFull;
                          const listed=myListings.some(l=>l.id===p.id);
                          return(
                            <div key={p.id} className="player-row"
                              onClick={()=>!disabled&&addToXI(p)}
                              style={{display:"flex",alignItems:"center",gap:10,
                                padding:"9px 10px",borderBottom:"1px solid #111120",
                                background:already?"#0b2219":"transparent",
                                opacity:disabled&&!already?0.35:1,
                                cursor:disabled?"default":"pointer"}}>
                              <div style={{width:32,height:32,borderRadius:"50%",flexShrink:0,
                                background:`linear-gradient(145deg,${CLUB_COLORS[p.club]||"#333"},${CLUB_COLORS[p.club]||"#333"}66)`,
                                display:"flex",alignItems:"center",justifyContent:"center",
                                fontFamily:"Anton,sans-serif",fontSize:11,color:"#fff",
                                border:`1.5px solid ${CLUB_COLORS[p.club]||"#555"}`}}>
                                {p.name.slice(0,2).toUpperCase()}
                              </div>
                              <div style={{flex:1,minWidth:0}}>
                                <div style={{display:"flex",alignItems:"center",gap:5}}>
                                  <span style={{fontSize:12,fontWeight:700,
                                    whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis",
                                    color:already?"#10b981":"#e8e8f0"}}>
                                    {p.name}
                                  </span>
                                  {already&&<span style={{fontSize:10,color:"#10b981"}}>✓</span>}
                                  {listed&&<span style={{fontSize:10}}>📤</span>}
                                </div>
                                <div style={{display:"flex",alignItems:"center",gap:4,marginTop:1}}>
                                  <ClubDot club={p.club}/>
                                  <span style={{fontSize:10,color:"#555"}}>{p.club}</span>
                                </div>
                              </div>
                              <div style={{textAlign:"right",flexShrink:0}}>
                                <div style={{fontSize:11,color:"#ffd700",fontWeight:700}}>{fmtM(p.value)}</div>
                                <TierBadge tier={p.squadTier||p.tier} t={t}/>
                              </div>
                              {!listed&&(
                                <button onClick={e=>{e.stopPropagation();setSellModal(p);setListPriceInput("");}} style={{
                                  background:"#1a0a0a",border:"1px solid #c8102e44",color:"#c8102e",
                                  fontSize:11,padding:"4px 7px",borderRadius:5,cursor:"pointer",flexShrink:0}}>
                                  {t.sellMode}
                                </button>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* ══ MARKET TAB ══ */}
          {tab==="market"&&market&&(
            <div style={{animation:"fadeUp .3s ease"}}>
              <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:12,flexWrap:"wrap",gap:8}}>
                <div>
                  <h2 style={{fontFamily:"Anton,sans-serif",fontSize:20,letterSpacing:1}}>{t.marketTitle}</h2>
                  <p style={{fontSize:11,color:"#555",marginTop:2}}>{t.marketSub}</p>
                </div>
                <div style={{display:"flex",gap:8,alignItems:"center"}}>
                  <div style={{background:"#0e0e1c",border:"1px solid #1a1a30",borderRadius:7,
                    padding:"4px 10px",fontSize:11,color:"#ffd700",fontWeight:700}}>
                    {t.transferBudget}: {fmtM(transferBudget)}
                  </div>
                  <button onClick={()=>setMarket(generateMarket(squad.map(p=>p.id)))} style={{
                    background:"#c8102e",color:"#fff",border:"none",padding:"7px 14px",
                    borderRadius:7,cursor:"pointer",fontWeight:700,fontSize:12}}>
                    🔄 {t.refresh}
                  </button>
                </div>
              </div>
              {/* Sub tabs */}
              <div style={{display:"flex",gap:6,marginBottom:12}}>
                {[{k:"buy",label:"🛒 Markt"},{k:"myListings",label:`📤 ${t.myListings} (${myListings.length})`}].map(tb=>(
                  <button key={tb.k} onClick={()=>setMarketTab(tb.k)} style={{
                    background:marketTab===tb.k?"#c8102e":"#0e0e1c",
                    border:`1px solid ${marketTab===tb.k?"#c8102e":"#1a1a30"}`,
                    color:"#fff",padding:"6px 14px",borderRadius:7,cursor:"pointer",fontWeight:700,fontSize:12}}>
                    {tb.label}
                  </button>
                ))}
              </div>
              {marketTab==="buy"&&(
                <div>
                  <div style={{background:"#0e0c05",border:"1px solid #ffd70025",borderRadius:8,
                    padding:"9px 12px",marginBottom:10,fontSize:12,color:"#aaa"}}>{t.blindNotice}</div>
                  <div style={{display:"flex",gap:8,marginBottom:12,flexWrap:"wrap"}}>
                    <input placeholder={t.searchPlayer} value={marketSearch}
                      onChange={e=>setMarketSearch(e.target.value)}
                      style={{background:"#0e0e1c",border:"1px solid #1a1a30",borderRadius:7,
                        padding:"7px 11px",fontSize:12,flex:1,minWidth:120}}/>
                    <select value={marketClub} onChange={e=>setMarketClub(e.target.value)}
                      style={{background:"#0e0e1c",border:"1px solid #1a1a30",color:"#fff",
                        borderRadius:7,padding:"7px 11px",fontSize:12,cursor:"pointer"}}>
                      <option value="ALL">{t.all}</option>
                      {allClubs.map(c=><option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                  <div style={{display:"flex",flexDirection:"column",gap:10}}>
                    {filteredMarket.map(listing=>{
                      const remaining=listing.expiresAt-now;
                      const urgent=remaining<3*3600*1000;
                      const curVal=players[listing.id]??listing.value;
                      return(
                        <div key={listing.marketId} style={{background:"#0e0e1c",borderRadius:12,padding:14,
                          border:`1px solid ${urgent?"#ef444433":"#1a1a30"}`,
                          display:"flex",gap:12,alignItems:"center",flexWrap:"wrap"}}>
                          <div style={{width:48,height:48,borderRadius:9,flexShrink:0,
                            background:`linear-gradient(135deg,${CLUB_COLORS[listing.club]||"#333"},${CLUB_COLORS[listing.club]||"#333"}55)`,
                            display:"flex",alignItems:"center",justifyContent:"center",
                            fontFamily:"Anton,sans-serif",fontSize:16,color:"#fff"}}>
                            {listing.name.slice(0,2).toUpperCase()}
                          </div>
                          <div style={{flex:1,minWidth:100}}>
                            <div style={{display:"flex",gap:6,alignItems:"center",marginBottom:3,flexWrap:"wrap"}}>
                              <span style={{fontWeight:700,fontSize:13}}>{listing.name}</span>
                              <PosBadge pos={listing.pos} t={t}/>
                              <TierBadge tier={listing.tier} t={t}/>
                            </div>
                            <div style={{fontSize:11,color:"#555",display:"flex",alignItems:"center",gap:4}}>
                              <ClubDot club={listing.club}/>{listing.club}
                            </div>
                            <div style={{display:"flex",gap:10,marginTop:4,flexWrap:"wrap"}}>
                              <span style={{fontSize:11,color:"#ffd700"}}>💰 {fmtM(curVal)}</span>
                              <span style={{fontSize:11,color:"#888"}}>⭐ {listing.form}</span>
                              <span style={{fontSize:11,color:urgent?"#ef4444":"#555"}}>⏱ {fmtTime(remaining)}</span>
                            </div>
                          </div>
                          <div style={{flexShrink:0}}>
                            {listing.submitted?(
                              <div style={{background:"#0a2015",border:"1px solid #10b981",
                                borderRadius:8,padding:"8px 12px",textAlign:"center"}}>
                                <div style={{fontSize:10,color:"#10b981",marginBottom:2}}>{t.bidDone}</div>
                                <div style={{fontFamily:"Anton,sans-serif",fontSize:16,color:"#ffd700"}}>{fmtM(listing.myBid)}</div>
                                <div style={{fontSize:10,color:"#555",marginTop:2}}>{t.bidResult}</div>
                              </div>
                            ):(
                              <div style={{display:"flex",gap:6,alignItems:"center"}}>
                                <input type="number" step="0.1" min="0.1" placeholder={t.bidPlaceholder}
                                  value={bidInputs[listing.marketId]||""}
                                  onChange={e=>setBidInputs(p=>({...p,[listing.marketId]:e.target.value}))}
                                  style={{background:"#14142a",border:"1px solid #1e1e38",
                                    padding:"7px 9px",borderRadius:7,width:100,fontSize:12}}/>
                                <button onClick={()=>submitBid(listing)} style={{
                                  background:"#c8102e",color:"#fff",border:"none",
                                  padding:"7px 12px",borderRadius:7,cursor:"pointer",fontWeight:700,fontSize:12}}>
                                  {t.submitBid}
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
              {marketTab==="myListings"&&(
                <div>
                  {myListings.length===0?(
                    <div style={{color:"#333",textAlign:"center",padding:40,fontSize:14}}>{t.noListings}</div>
                  ):(
                    <div style={{display:"flex",flexDirection:"column",gap:10}}>
                      {myListings.map(l=>{
                        const remaining=l.expiresAt-now;
                        return(
                          <div key={l.marketId} style={{background:"#0e0e1c",borderRadius:12,padding:14,
                            border:"1px solid #f5c51844",display:"flex",gap:12,alignItems:"center"}}>
                            <div style={{width:46,height:46,borderRadius:9,flexShrink:0,
                              background:`linear-gradient(135deg,${CLUB_COLORS[l.club]||"#333"},${CLUB_COLORS[l.club]||"#333"}55)`,
                              display:"flex",alignItems:"center",justifyContent:"center",
                              fontFamily:"Anton,sans-serif",fontSize:15,color:"#fff"}}>
                              {l.name.slice(0,2).toUpperCase()}
                            </div>
                            <div style={{flex:1}}>
                              <div style={{fontWeight:700,fontSize:13}}>{l.name}</div>
                              <div style={{fontSize:11,color:"#555",marginTop:2,display:"flex",alignItems:"center",gap:4}}>
                                <ClubDot club={l.club}/>{l.club}
                              </div>
                              <div style={{display:"flex",gap:10,marginTop:4}}>
                                <span style={{fontSize:11,color:"#f5c518",fontWeight:700}}>
                                  {t.listedFor}: {fmtM(l.askPrice)}
                                </span>
                                <span style={{fontSize:11,color:remaining<3*3600*1000?"#ef4444":"#555"}}>
                                  ⏱ {fmtTime(remaining)}
                                </span>
                              </div>
                            </div>
                            <button onClick={()=>{
                              setMyListings(prev=>prev.filter(x=>x.marketId!==l.marketId));
                              setMarket(prev=>prev.filter(x=>x.marketId!==l.marketId));
                              notify(lang==="de"?"Angebot zurückgezogen":"Teklif geri alındı");
                            }} style={{background:"#1a0a0a",border:"1px solid #c8102e44",color:"#c8102e",
                              fontSize:12,padding:"5px 9px",borderRadius:6,cursor:"pointer",flexShrink:0}}>✕</button>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* ══ LIVE TAB ══ */}
          {tab==="live"&&(
            <div style={{animation:"fadeUp .3s ease"}}>
              <h2 style={{fontFamily:"Anton,sans-serif",fontSize:20,letterSpacing:1,marginBottom:4}}>{t.liveTitle}</h2>
              <p style={{fontSize:11,color:"#555",marginBottom:12}}>{t.liveSub}</p>
              <div style={{display:"flex",gap:8,marginBottom:12,flexWrap:"wrap"}}>
                {MATCH_DATA.map(m=>(
                  <button key={m.id} onClick={()=>{setActiveMatch(m.id);setLiveMin(0);setLiveRunning(false);setShownEvents([]);}} style={{
                    background:activeMatch===m.id?"#c8102e":"#0e0e1c",
                    border:`1px solid ${activeMatch===m.id?"#c8102e":"#1a1a30"}`,
                    color:"#fff",padding:"8px 12px",borderRadius:8,cursor:"pointer",fontSize:12,fontWeight:600}}>
                    <div style={{fontSize:10,color:"rgba(255,255,255,.4)",marginBottom:2}}>
                      Hafta {m.matchday} · {m.date}
                    </div>
                    {m.home} vs {m.away}
                  </button>
                ))}
              </div>
              <div style={{background:"#0e0e1c",borderRadius:12,padding:18,marginBottom:12,border:"1px solid #1a1a30"}}>
                <div style={{display:"flex",alignItems:"center",justifyContent:"center",gap:20,marginBottom:14}}>
                  <div style={{textAlign:"center"}}>
                    <div style={{width:12,height:12,borderRadius:"50%",
                      background:CLUB_COLORS[currentMatch?.home]||"#555",margin:"0 auto 5px"}}/>
                    <div style={{fontWeight:700,fontSize:14}}>{currentMatch?.home}</div>
                  </div>
                  <div style={{textAlign:"center"}}>
                    <div style={{fontFamily:"Anton,sans-serif",fontSize:44,color:"#ffd700",lineHeight:1}}>
                      {shownEvents.filter(e=>e.club===currentMatch?.home&&e.type==="tor").length}
                      {" : "}
                      {shownEvents.filter(e=>e.club===currentMatch?.away&&e.type==="tor").length}
                    </div>
                    <div style={{fontSize:11,color:"#555",marginTop:3}}>{liveMin}' / 90'</div>
                  </div>
                  <div style={{textAlign:"center"}}>
                    <div style={{width:12,height:12,borderRadius:"50%",
                      background:CLUB_COLORS[currentMatch?.away]||"#555",margin:"0 auto 5px"}}/>
                    <div style={{fontWeight:700,fontSize:14}}>{currentMatch?.away}</div>
                  </div>
                </div>
                <div style={{background:"#14142a",borderRadius:5,height:5,marginBottom:12}}>
                  <div style={{background:"#c8102e",borderRadius:5,height:"100%",
                    width:`${(liveMin/90)*100}%`,transition:"width .2s"}}/>
                </div>
                <div style={{display:"flex",justifyContent:"center",gap:10}}>
                  <button onClick={()=>{setLiveRunning(!liveRunning);if(liveMin>=90){setLiveMin(0);setShownEvents([]);}}} style={{
                    background:liveRunning?"#ef4444":"#10b981",color:"#fff",border:"none",
                    padding:"10px 22px",borderRadius:9,cursor:"pointer",fontWeight:700,fontSize:13}}>
                    {liveRunning?t.pauseBtn:liveMin>=90?t.restartBtn:t.startBtn}
                  </button>
                  <button onClick={()=>{setLiveMin(0);setLiveRunning(false);setShownEvents([]);}} style={{
                    background:"#1a1a2e",color:"#888",border:"none",padding:"10px 14px",
                    borderRadius:9,cursor:"pointer",fontSize:12}}>
                    {t.resetBtn}
                  </button>
                </div>
              </div>
              {xi.length>0&&(
                <div style={{background:"linear-gradient(135deg,#c8102e14,#0e0e1c)",
                  border:"1px solid #c8102e33",borderRadius:10,padding:"12px 16px",
                  marginBottom:12,display:"flex",justifyContent:"space-between",alignItems:"center"}}>
                  <div>
                    <div style={{fontSize:11,color:"#888"}}>{t.myMatchPts}</div>
                    <div style={{fontSize:11,color:"#555",marginTop:1}}>
                      {xi.filter(p=>currentMatch?.events.some(e=>e.player===p.name)).length} {t.myPlayers}
                    </div>
                  </div>
                  <div style={{fontFamily:"Anton,sans-serif",fontSize:44,
                    color:myLivePts>=0?"#10b981":"#ef4444",lineHeight:1}}>
                    {myLivePts>=0?"+":""}{myLivePts.toFixed(1)}
                  </div>
                </div>
              )}
              <div style={{background:"#0e0e1c",borderRadius:10,padding:14,border:"1px solid #1a1a30"}}>
                <div style={{fontSize:10,color:"#555",letterSpacing:1,marginBottom:10}}>{t.eventsTitle}</div>
                {shownEvents.length===0&&<div style={{color:"#2a2a40",textAlign:"center",padding:24,fontSize:12}}>{t.noEvents}</div>}
                {shownEvents.map((ev,i)=>{
                  const isMine=xi.some(p=>p.name===ev.player);
                  return(
                    <div key={i} style={{display:"flex",justifyContent:"space-between",alignItems:"center",
                      padding:"9px 12px",borderRadius:8,marginBottom:6,
                      background:isMine?"#0a2015":"#12122a",
                      border:`1px solid ${isMine?"#10b98140":"#1a1a38"}`,
                      animation:i===0?"fadeSlide .3s ease":"none"}}>
                      <div style={{display:"flex",gap:8,alignItems:"center"}}>
                        <span style={{fontFamily:"Anton,sans-serif",fontSize:14,color:"#444",width:26}}>{ev.min}'</span>
                        <ClubDot club={ev.club}/>
                        <div>
                          <span style={{fontWeight:700,fontSize:12}}>{ev.player}</span>
                          <span style={{fontSize:10,color:"#666",marginLeft:5}}>{evLabels[ev.type]||ev.type}</span>
                          {isMine&&<span style={{fontSize:9,color:"#10b981",marginLeft:5,fontWeight:700}}>{t.myPlayer}</span>}
                        </div>
                      </div>
                      <span style={{fontFamily:"Anton,sans-serif",fontSize:18,
                        color:ev.pts>=0?"#10b981":"#ef4444"}}>
                        {ev.pts>=0?"+":""}{ev.pts}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* ══ RANKING TAB ══ */}
          {tab==="ranking"&&(
            <div style={{animation:"fadeUp .3s ease"}}>
              <h2 style={{fontFamily:"Anton,sans-serif",fontSize:20,letterSpacing:1,marginBottom:4}}>{t.rankTitle}</h2>
              <p style={{fontSize:11,color:"#555",marginBottom:14}}>{t.rankSub}</p>
              <div style={{background:"#0e0e1c",borderRadius:12,overflow:"hidden",border:"1px solid #1a1a30"}}>
                <div style={{display:"grid",gridTemplateColumns:"40px 1fr 80px 80px",
                  padding:"8px 16px",borderBottom:"1px solid #141428",
                  fontSize:10,color:"#444",letterSpacing:1,fontWeight:700}}>
                  <span>#</span><span>{t.managerCol}</span>
                  <span style={{textAlign:"right"}}>{t.weekCol}</span>
                  <span style={{textAlign:"right"}}>{t.seasonCol}</span>
                </div>
                {lb.map((e,i)=>(
                  <div key={i} style={{display:"grid",gridTemplateColumns:"40px 1fr 80px 80px",
                    alignItems:"center",padding:"12px 16px",borderBottom:"1px solid #0e0e1e",
                    background:e.isMe?"linear-gradient(90deg,#c8102e0d,transparent)":"transparent"}}>
                    <div style={{fontFamily:"Anton,sans-serif",fontSize:20,
                      color:i===0?"#ffd700":i===1?"#c0c0c0":i===2?"#cd7f32":"#2a2a40"}}>{i+1}</div>
                    <div style={{display:"flex",alignItems:"center",gap:8}}>
                      <div style={{width:28,height:28,borderRadius:6,
                        background:e.isMe?"#c8102e":"#1a1a2e",
                        display:"flex",alignItems:"center",justifyContent:"center",
                        fontSize:13,fontWeight:700,color:"#fff"}}>
                        {e.name.slice(0,1)}
                      </div>
                      <span style={{fontWeight:e.isMe?700:500,color:e.isMe?"#ffd700":"#e8e8f0",fontSize:13}}>
                        {e.name}{e.isMe&&" 👈"}
                      </span>
                    </div>
                    <div style={{textAlign:"right",fontSize:13,color:"#10b981",fontWeight:600}}>+{e.weekly.toFixed(1)}</div>
                    <div style={{textAlign:"right",fontFamily:"Anton,sans-serif",fontSize:22,color:"#ffd700"}}>{e.pts.toFixed(0)}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ══ RULES TAB ══ */}
          {tab==="rules"&&(
            <div style={{animation:"fadeUp .3s ease"}}>
              <h2 style={{fontFamily:"Anton,sans-serif",fontSize:20,letterSpacing:1,marginBottom:4}}>{t.rulesTitle}</h2>
              <p style={{fontSize:11,color:"#555",marginBottom:14}}>{t.rulesSub}</p>
              <div style={{display:"grid",gap:8}}>
                {POINT_RULES.map((r,i)=>(
                  <div key={i} style={{background:"#0e0e1c",borderRadius:10,padding:"12px 16px",
                    display:"flex",justifyContent:"space-between",alignItems:"center",border:"1px solid #141428"}}>
                    <div style={{fontWeight:600,fontSize:13}}>{lang==="tr"?EV_TR[r.type]:EV_DE[r.type]}</div>
                    <div style={{fontFamily:"Anton,sans-serif",fontSize:24,color:r.c}}>{r.pts}</div>
                  </div>
                ))}
              </div>
              <div style={{marginTop:20,background:"#060e0a",border:"1px solid #10b98128",borderRadius:10,padding:14}}>
                <div style={{fontFamily:"Anton,sans-serif",fontSize:14,letterSpacing:1,color:"#10b981",marginBottom:6}}>
                  📈 {t.mwChange}
                </div>
                <p style={{fontSize:12,color:"#777",lineHeight:1.6}}>{t.mwInfo}</p>
                <div style={{marginTop:10,display:"flex",gap:16,flexWrap:"wrap"}}>
                  <span style={{color:"#10b981",fontWeight:700}}>↑ {t.mwUp}</span>
                  <span style={{color:"#ef4444",fontWeight:700}}>↓ {t.mwDown}</span>
                  <span style={{color:"#888",fontWeight:700}}>→ {t.mwStable}</span>
                </div>
              </div>
            </div>
          )}

        </div>
      </main>
    </div>
  );
}
