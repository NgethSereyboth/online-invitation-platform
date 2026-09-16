(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define([], factory);
  } else if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    var exp = factory();
    root.momentkh = exp;
    root.MoonPhase = exp.MoonPhase;
    root.MonthIndex = exp.MonthIndex;
    root.AnimalYear = exp.AnimalYear;
    root.AnimalYearEmojis = exp.AnimalYearEmojis;
    root.Sak = exp.Sak;
    root.DayOfWeek = exp.DayOfWeek;
  }
}(typeof self !== 'undefined' ? self : this, function () {
  var module = { exports: {} };
  var exports = module.exports;

  "use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.constants = exports.DayOfWeek = exports.Sak = exports.AnimalYear = exports.MonthIndex = exports.MoonPhase = void 0;
exports.fromGregorian = fromGregorian;
exports.fromKhmer = fromKhmer;
exports.getNewYear = getNewYear;
exports.format = format;
exports.fromDate = fromDate;
exports.toDate = toDate;
var MoonPhase;
(function (MoonPhase) {
    MoonPhase[MoonPhase["Waxing"] = 0] = "Waxing";
    MoonPhase[MoonPhase["Waning"] = 1] = "Waning"; // រោច
})(MoonPhase || (exports.MoonPhase = MoonPhase = {}));
var MonthIndex;
(function (MonthIndex) {
    MonthIndex[MonthIndex["Migasir"] = 0] = "Migasir";
    MonthIndex[MonthIndex["Boss"] = 1] = "Boss";
    MonthIndex[MonthIndex["Meak"] = 2] = "Meak";
    MonthIndex[MonthIndex["Phalkun"] = 3] = "Phalkun";
    MonthIndex[MonthIndex["Cheit"] = 4] = "Cheit";
    MonthIndex[MonthIndex["Pisakh"] = 5] = "Pisakh";
    MonthIndex[MonthIndex["Jesth"] = 6] = "Jesth";
    MonthIndex[MonthIndex["Asadh"] = 7] = "Asadh";
    MonthIndex[MonthIndex["Srap"] = 8] = "Srap";
    MonthIndex[MonthIndex["Phatrabot"] = 9] = "Phatrabot";
    MonthIndex[MonthIndex["Assoch"] = 10] = "Assoch";
    MonthIndex[MonthIndex["Kadeuk"] = 11] = "Kadeuk";
    MonthIndex[MonthIndex["Pathamasadh"] = 12] = "Pathamasadh";
    MonthIndex[MonthIndex["Tutiyasadh"] = 13] = "Tutiyasadh"; // ទុតិយាសាឍ
})(MonthIndex || (exports.MonthIndex = MonthIndex = {}));
var AnimalYear;
(function (AnimalYear) {
    AnimalYear[AnimalYear["Chhut"] = 0] = "Chhut";
    AnimalYear[AnimalYear["Chlov"] = 1] = "Chlov";
    AnimalYear[AnimalYear["Khal"] = 2] = "Khal";
    AnimalYear[AnimalYear["Thos"] = 3] = "Thos";
    AnimalYear[AnimalYear["Rong"] = 4] = "Rong";
    AnimalYear[AnimalYear["Masagn"] = 5] = "Masagn";
    AnimalYear[AnimalYear["Momee"] = 6] = "Momee";
    AnimalYear[AnimalYear["Momae"] = 7] = "Momae";
    AnimalYear[AnimalYear["Vok"] = 8] = "Vok";
    AnimalYear[AnimalYear["Roka"] = 9] = "Roka";
    AnimalYear[AnimalYear["Cho"] = 10] = "Cho";
    AnimalYear[AnimalYear["Kor"] = 11] = "Kor"; // កុរ - Pig
})(AnimalYear || (exports.AnimalYear = AnimalYear = {}));
var Sak;
(function (Sak) {
    Sak[Sak["SamridhiSak"] = 0] = "SamridhiSak";
    Sak[Sak["AekSak"] = 1] = "AekSak";
    Sak[Sak["ToSak"] = 2] = "ToSak";
    Sak[Sak["TreiSak"] = 3] = "TreiSak";
    Sak[Sak["ChattvaSak"] = 4] = "ChattvaSak";
    Sak[Sak["PanchaSak"] = 5] = "PanchaSak";
    Sak[Sak["ChhaSak"] = 6] = "ChhaSak";
    Sak[Sak["SappaSak"] = 7] = "SappaSak";
    Sak[Sak["AtthaSak"] = 8] = "AtthaSak";
    Sak[Sak["NappaSak"] = 9] = "NappaSak"; // នព្វស័ក
})(Sak || (exports.Sak = Sak = {}));
var DayOfWeek;
(function (DayOfWeek) {
    DayOfWeek[DayOfWeek["Sunday"] = 0] = "Sunday";
    DayOfWeek[DayOfWeek["Monday"] = 1] = "Monday";
    DayOfWeek[DayOfWeek["Tuesday"] = 2] = "Tuesday";
    DayOfWeek[DayOfWeek["Wednesday"] = 3] = "Wednesday";
    DayOfWeek[DayOfWeek["Thursday"] = 4] = "Thursday";
    DayOfWeek[DayOfWeek["Friday"] = 5] = "Friday";
    DayOfWeek[DayOfWeek["Saturday"] = 6] = "Saturday"; // សៅរ៍
})(DayOfWeek || (exports.DayOfWeek = DayOfWeek = {}));
const LunarMonths = {
    'មិគសិរ': 0, 'បុស្ស': 1, 'មាឃ': 2, 'ផល្គុន': 3,
    'ចេត្រ': 4, 'ពិសាខ': 5, 'ជេស្ឋ': 6, 'អាសាឍ': 7,
    'ស្រាពណ៍': 8, 'ភទ្របទ': 9, 'អស្សុជ': 10, 'កត្ដិក': 11,
    'បឋមាសាឍ': 12, 'ទុតិយាសាឍ': 13
};
const LunarMonthNames = [
    'មិគសិរ', 'បុស្ស', 'មាឃ', 'ផល្គុន', 'ចេត្រ', 'ពិសាខ',
    'ជេស្ឋ', 'អាសាឍ', 'ស្រាពណ៍', 'ភទ្របទ', 'អស្សុជ', 'កត្ដិក',
    'បឋមាសាឍ', 'ទុតិយាសាឍ'
];
const SolarMonthNames = [
    'មករា', 'កុម្ភៈ', 'មីនា', 'មេសា', 'ឧសភា', 'មិថុនា',
    'កក្កដា', 'សីហា', 'កញ្ញា', 'តុលា', 'វិច្ឆិកា', 'ធ្នូ'
];
const SolarMonthAbbreviationNames = [
    'មក', 'កម', 'មន', 'មស', 'ឧស', 'មថ',
    'កដ', 'សហ', 'កញ', 'តល', 'វក', 'ធន'
];
const LunarMonthAbbreviationNames = [
    'មិ', 'បុ', 'មា', 'ផល', 'ចេ', 'ពិ',
    'ជេ', 'អា', 'ស្រ', 'ភ', 'អ', 'ក',
    'បឋ', 'ទុតិ'
];
const AnimalYearNames = [
    'ជូត', 'ឆ្លូវ', 'ខាល', 'ថោះ', 'រោង', 'ម្សាញ់',
    'មមី', 'មមែ', 'វក', 'រកា', 'ច', 'កុរ'
];
const AnimalYearEmojis = [
    '🐀', '🐂', '🐅', '🐇', '🐉', '🐍',
    '🐎', '🐐', '🐒', '🐓', '🐕', '🐖'
];
const SakNames = [
    'សំរឹទ្ធិស័ក', 'ឯកស័ក', 'ទោស័ក', 'ត្រីស័ក', 'ចត្វាស័ក',
    'បញ្ចស័ក', 'ឆស័ក', 'សប្តស័ក', 'អដ្ឋស័ក', 'នព្វស័ក'
];
const WeekdayNames = [
    'អាទិត្យ', 'ចន្ទ', 'អង្គារ', 'ពុធ', 'ព្រហស្បតិ៍', 'សុក្រ', 'សៅរ៍'
];
const WeekdayNamesShort = ['អា', 'ច', 'អ', 'ព', 'ព្រ', 'សុ', 'ស'];
const MoonPhaseNames = ['កើត', 'រោច'];
const MoonPhaseShort = ['ក', 'រ'];
const MoonDaySymbols = [
    '᧡', '᧢', '᧣', '᧤', '᧥', '᧦', '᧧', '᧨', '᧩', '᧪',
    '᧫', '᧬', '᧭', '᧮', '᧯', '᧱', '᧲', '᧳', '᧴', '᧵',
    '᧶', '᧷', '᧸', '᧹', '᧺', '᧻', '᧼', '᧽', '᧾', '᧿'
];
const KhmerNumerals = {
    '0': '០', '1': '១', '2': '២', '3': '៣', '4': '៤',
    '5': '៥', '6': '៦', '7': '៧', '8': '៨', '9': '៩'
};
const khNewYearMoments = {
    '1879': '12-04-1879 11:36',
    '1897': '13-04-1897 02:00',
    '2011': '14-04-2011 13:12',
    '2012': '14-04-2012 19:11',
    '2013': '14-04-2013 02:12',
    '2014': '14-04-2014 08:07',
    '2015': '14-04-2015 14:02',
    '2024': '13-04-2024 22:17',
};
function toKhmerNumeral(num) {
    return String(num).replace(/\d/g, d => KhmerNumerals[d]);
}
function isGregorianLeapYear(year) {
    return (year % 4 === 0 && year % 100 !== 0) || (year % 400 === 0);
}
function getDaysInGregorianMonth(year, month) {
    const daysInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    if (month === 2 && isGregorianLeapYear(year)) {
        return 29;
    }
    return daysInMonth[month - 1];
}
function gregorianToJulianDay(year, month, day) {
    const a = Math.floor((14 - month) / 12);
    const y = year + 4800 - a;
    const m = month + 12 * a - 3;
    return day + Math.floor((153 * m + 2) / 5) + 365 * y +
        Math.floor(y / 4) - Math.floor(y / 100) + Math.floor(y / 400) - 32045;
}
function julianDayToGregorian(jdn) {
    const a = jdn + 32044;
    const b = Math.floor((4 * a + 3) / 146097);
    const c = a - Math.floor((146097 * b) / 4);
    const d = Math.floor((4 * c + 3) / 1461);
    const e = c - Math.floor((1461 * d) / 4);
    const m = Math.floor((5 * e + 2) / 153);
    const day = e - Math.floor((153 * m + 2) / 5) + 1;
    const month = m + 3 - 12 * Math.floor(m / 10);
    const year = 100 * b + d - 4800 + Math.floor(m / 10);
    return { year, month, day };
}
function getDayOfWeek(year, month, day) {
    const jdn = gregorianToJulianDay(year, month, day);
    return (jdn + 1) % 7;
}
function validateGregorianDate(year, month, day, hour = 0, minute = 0, second = 0) {
    if (typeof year !== 'number' || isNaN(year)) {
        throw new Error(`Invalid year: ${year}. Year must be a valid number.`);
    }
    if (typeof month !== 'number' || isNaN(month)) {
        throw new Error(`Invalid month: ${month}. Month must be a valid number.`);
    }
    if (typeof day !== 'number' || isNaN(day)) {
        throw new Error(`Invalid day: ${day}. Day must be a valid number.`);
    }
    if (typeof hour !== 'number' || isNaN(hour)) {
        throw new Error(`Invalid hour: ${hour}. Hour must be a valid number.`);
    }
    if (typeof minute !== 'number' || isNaN(minute)) {
        throw new Error(`Invalid minute: ${minute}. Minute must be a valid number.`);
    }
    if (typeof second !== 'number' || isNaN(second)) {
        throw new Error(`Invalid second: ${second}. Second must be a valid number.`);
    }
    if (month < 1 || month > 12) {
        throw new Error(`Invalid month: ${month}. Month must be between 1 and 12.`);
    }
    const daysInMonth = getDaysInGregorianMonth(year, month);
    if (day < 1 || day > daysInMonth) {
        const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'];
        throw new Error(`Invalid day: ${day}. ${monthNames[month - 1]} ${year} has ${daysInMonth} days.`);
    }
    if (hour < 0 || hour > 23) {
        throw new Error(`Invalid hour: ${hour}. Hour must be between 0 and 23.`);
    }
    if (minute < 0 || minute > 59) {
        throw new Error(`Invalid minute: ${minute}. Minute must be between 0 and 59.`);
    }
    if (second < 0 || second > 59) {
        throw new Error(`Invalid second: ${second}. Second must be between 0 and 59.`);
    }
}
function validateKhmerDate(day, moonPhase, monthIndex, beYear) {
    if (typeof day !== 'number' || isNaN(day)) {
        throw new Error(`Invalid day: ${day}. Day must be a valid number.`);
    }
    if (typeof moonPhase !== 'number' || isNaN(moonPhase)) {
        throw new Error(`Invalid moonPhase: ${moonPhase}. moonPhase must be a valid number.`);
    }
    if (typeof monthIndex !== 'number' || isNaN(monthIndex)) {
        throw new Error(`Invalid monthIndex: ${monthIndex}. monthIndex must be a valid number.`);
    }
    if (typeof beYear !== 'number' || isNaN(beYear)) {
        throw new Error(`Invalid beYear: ${beYear}. beYear must be a valid number.`);
    }
    if (day < 1 || day > 15) {
        throw new Error(`Invalid day: ${day}. Lunar day must be between 1 and 15.`);
    }
    const moonPhaseNum = typeof moonPhase === 'number' ? moonPhase : moonPhase;
    if (moonPhaseNum !== 0 && moonPhaseNum !== 1) {
        throw new Error(`Invalid moonPhase: ${moonPhase}. moonPhase must be 0 (Waxing/កើត) or 1 (Waning/រោច).`);
    }
    const monthIndexNum = typeof monthIndex === 'number' ? monthIndex : monthIndex;
    if (monthIndexNum < 0 || monthIndexNum > 13) {
        throw new Error(`Invalid monthIndex: ${monthIndex}. monthIndex must be between 0 and 13.`);
    }
    if (beYear < 2000 || beYear > 3000) {
        throw new Error(`Invalid beYear: ${beYear}. beYear must be between 2000 and 3000.`);
    }
}
function validateDateObject(date) {
    if (!(date instanceof Date)) {
        throw new Error('Invalid input: Expected a Date object.');
    }
    if (isNaN(date.getTime())) {
        throw new Error('Invalid Date object: Date is not a valid date.');
    }
}
function adToJs(adYear) {
    return adYear - 638;
}
function adToBe(adYear) {
    return adYear + 544;
}
function beToAd(beYear) {
    return beYear - 544;
}
function jsToAd(jsYear) {
    return jsYear + 638;
}
function beToJs(beYear) {
    return beYear - 1182;
}
function jsToBe(jsYear) {
    return jsYear + 1182;
}
function getAharkun(beYear) {
    return Math.floor((beYear * 292207 + 499) / 800) + 4;
}
function getAharkunMod(beYear) {
    return (beYear * 292207 + 499) % 800;
}
function getKromthupul(beYear) {
    return 800 - getAharkunMod(beYear);
}
function getAvoman(beYear) {
    return (getAharkun(beYear) * 11 + 25) % 692;
}
function getBodithey(beYear) {
    const aharkun = getAharkun(beYear);
    return (Math.floor((aharkun * 11 + 25) / 692) + aharkun + 29) % 30;
}
function isKhmerSolarLeap(beYear) {
    return getKromthupul(beYear) <= 207;
}
function isKhmerLeapDayByCalculation(beYear) {
    const avoman = getAvoman(beYear);
    const isSolarLeap = isKhmerSolarLeap(beYear);
    if (avoman === 0 && getAvoman(beYear - 1) === 137) {
        return true;
    }
    else if (isSolarLeap) {
        return avoman < 127;
    }
    else if (avoman === 137 && getAvoman(beYear + 1) === 0) {
        return false;
    }
    else if (avoman < 138) {
        return true;
    }
    return false;
}
function isKhmerLeapMonth(beYear) {
    const bodithey = getBodithey(beYear);
    const boditheyNextYear = getBodithey(beYear + 1);
    if (bodithey === 25 && boditheyNextYear === 5) {
        return false;
    }
    return (bodithey === 24 && boditheyNextYear === 6) ||
        (bodithey >= 25) ||
        (bodithey < 6);
}
function getLeapType(beYear) {
    if (isKhmerLeapMonth(beYear)) {
        return 1; // Leap month (អធិកមាស)
    }
    else if (isKhmerLeapDayByCalculation(beYear)) {
        return 2; // Leap day (ចន្ទ្រាធិមាស)
    }
    else if (isKhmerLeapMonth(beYear - 1)) {
        let previousYear = beYear - 1;
        while (true) {
            if (isKhmerLeapDayByCalculation(previousYear)) {
                return 2;
            }
            previousYear -= 1;
            if (!isKhmerLeapMonth(previousYear)) {
                return 0;
            }
        }
    }
    return 0; // Regular year
}
function getNumberOfDaysInKhmerMonth(monthIndex, beYear) {
    const leapType = getLeapType(beYear);
    const idx = typeof monthIndex === 'number' ? monthIndex : monthIndex;
    if (idx === MonthIndex.Jesth && leapType === 2) { // ជេស្ឋ with leap day
        return 30;
    }
    if (idx === MonthIndex.Pathamasadh || idx === MonthIndex.Tutiyasadh) { // បឋមាសាឍ, ទុតិយាសាឍ
        return leapType === 1 ? 30 : 0;
    }
    return idx % 2 === 0 ? 29 : 30;
}
function getNumberOfDaysInKhmerYear(beYear) {
    const leapType = getLeapType(beYear);
    if (leapType === 1)
        return 384; // Leap month
    if (leapType === 2)
        return 355; // Leap day
    return 354; // Regular
}
function nextMonthOf(monthIndex, beYear) {
    const leapType = getLeapType(beYear);
    const idx = typeof monthIndex === 'number' ? monthIndex : monthIndex;
    if (idx === MonthIndex.Jesth && leapType === 1) { // ជេស្ឋ in leap month year
        return MonthIndex.Pathamasadh; // បឋមាសាឍ
    }
    if (idx === MonthIndex.Kadeuk)
        return MonthIndex.Migasir; // កត្ដិក -> មិគសិរ
    if (idx === MonthIndex.Pathamasadh)
        return MonthIndex.Tutiyasadh; // បឋមាសាឍ -> ទុតិយាសាឍ
    if (idx === MonthIndex.Tutiyasadh)
        return MonthIndex.Srap; // ទុតិយាសាឍ -> ស្រាពណ៍
    return (idx + 1);
}
function previousMonthOf(monthIndex, beYear) {
    const leapType = getLeapType(beYear);
    const idx = typeof monthIndex === 'number' ? monthIndex : monthIndex;
    if (idx === MonthIndex.Migasir)
        return MonthIndex.Kadeuk; // មិគសិរ -> កត្ដិក
    if (idx === MonthIndex.Srap && leapType === 1)
        return MonthIndex.Tutiyasadh; // ស្រាពណ៍ -> ទុតិយាសាឍ (leap)
    if (idx === MonthIndex.Tutiyasadh)
        return MonthIndex.Pathamasadh; // ទុតិយាសាឍ -> បឋមាសាឍ
    if (idx === MonthIndex.Pathamasadh)
        return MonthIndex.Jesth; // បឋមាសាឍ -> ជេស្ឋ
    return (idx - 1);
}
function getAharkunJs(jsYear) {
    const h = jsYear * 292207 + 373;
    return Math.floor(h / 800) + 1;
}
function getAvomanJs(jsYear) {
    return (getAharkunJs(jsYear) * 11 + 650) % 692;
}
function getKromthupulJs(jsYear) {
    return 800 - ((292207 * jsYear + 373) % 800);
}
function getBoditheyJs(jsYear) {
    const aharkun = getAharkunJs(jsYear);
    const a = 11 * aharkun + 650;
    return (aharkun + Math.floor(a / 692)) % 30;
}
function isAdhikameas(jsYear) {
    const bodithey = getBoditheyJs(jsYear);
    const boditheyNext = getBoditheyJs(jsYear + 1);
    if (bodithey === 24 && boditheyNext === 6)
        return true;
    if (bodithey === 25 && boditheyNext === 5)
        return false;
    return bodithey > 24 || bodithey < 6;
}
function isChantrathimeas(jsYear) {
    const avoman = getAvomanJs(jsYear);
    const avomanNext = getAvomanJs(jsYear + 1);
    const avomanPrev = getAvomanJs(jsYear - 1);
    const isSolarLeap = getKromthupulJs(jsYear) <= 207;
    if (avoman === 0 && avomanPrev === 137)
        return true;
    if (isSolarLeap)
        return avoman < 127;
    if (avoman === 137 && avomanNext === 0)
        return false;
    if (!isSolarLeap && avoman < 138)
        return true;
    if (avomanPrev === 137 && avoman === 0)
        return true;
    return false;
}
function has366Days(jsYear) {
    return getKromthupulJs(jsYear) <= 207;
}
function getSunInfo(jsYear, sotin) {
    const infoOfPrevYear = {
        kromathopol: getKromthupulJs(jsYear - 1)
    };
    const r2 = 800 * sotin + infoOfPrevYear.kromathopol;
    const reasey = Math.floor(r2 / 24350);
    const r3 = r2 % 24350;
    const angsar = Math.floor(r3 / 811);
    const r4 = r3 % 811;
    const l1 = Math.floor(r4 / 14);
    const libda = l1 - 3;
    const sunAverageAsLibda = (30 * 60 * reasey) + (60 * angsar) + libda;
    const s1 = ((30 * 60 * 2) + (60 * 20));
    let leftOver = sunAverageAsLibda - s1;
    if (sunAverageAsLibda < s1) {
        leftOver += (30 * 60 * 12);
    }
    const kaen = Math.floor(leftOver / (30 * 60));
    let rs = -1;
    if ([0, 1, 2].includes(kaen)) {
        rs = kaen;
    }
    else if ([3, 4, 5].includes(kaen)) {
        rs = (30 * 60 * 6) - leftOver;
    }
    else if ([6, 7, 8].includes(kaen)) {
        rs = leftOver - (30 * 60 * 6);
    }
    else if ([9, 10, 11].includes(kaen)) {
        rs = ((30 * 60 * 11) + (60 * 29) + 60) - leftOver;
    }
    const lastLeftOver = {
        reasey: Math.floor(rs / (30 * 60)),
        angsar: Math.floor((rs % (30 * 60)) / 60),
        libda: rs % 60
    };
    let khan, pouichalip;
    if (lastLeftOver.angsar >= 15) {
        khan = 2 * lastLeftOver.reasey + 1;
        pouichalip = 60 * (lastLeftOver.angsar - 15) + lastLeftOver.libda;
    }
    else {
        khan = 2 * lastLeftOver.reasey;
        pouichalip = 60 * lastLeftOver.angsar + lastLeftOver.libda;
    }
    const chhayaSunMap = [
        { multiplicity: 35, chhaya: 0 },
        { multiplicity: 32, chhaya: 35 },
        { multiplicity: 27, chhaya: 67 },
        { multiplicity: 22, chhaya: 94 },
        { multiplicity: 13, chhaya: 116 },
        { multiplicity: 5, chhaya: 129 }
    ];
    const chhayaSun = khan <= 5 ? chhayaSunMap[khan] : { multiplicity: 0, chhaya: 134 };
    const q = Math.floor((pouichalip * chhayaSun.multiplicity) / 900);
    const pholAsLibda = q + chhayaSun.chhaya;
    const sunInaugurationAsLibda = kaen <= 5
        ? sunAverageAsLibda - pholAsLibda
        : sunAverageAsLibda + pholAsLibda;
    return {
        sunInaugurationAsLibda,
        reasey: Math.floor(sunInaugurationAsLibda / (30 * 60)),
        angsar: Math.floor((sunInaugurationAsLibda % (30 * 60)) / 60),
        libda: sunInaugurationAsLibda % 60
    };
}
function getNewYearInfo(jsYear) {
    const sotins = has366Days(jsYear - 1)
        ? [363, 364, 365, 366]
        : [362, 363, 364, 365];
    const newYearsDaySotins = sotins.map(sotin => getSunInfo(jsYear, sotin));
    let timeOfNewYear = { hour: 0, minute: 0 };
    for (const sotin of newYearsDaySotins) {
        if (sotin.angsar === 0) {
            const minutes = (24 * 60) - (sotin.libda * 24);
            timeOfNewYear = {
                hour: Math.floor(minutes / 60) % 24,
                minute: minutes % 60
            };
            break;
        }
    }
    const numberOfVanabatDays = (newYearsDaySotins[0].angsar === 0) ? 2 : 1;
    return {
        timeOfNewYear,
        numberOfVanabatDays,
        newYearsDaySotins
    };
}
class KhmerDate {
    constructor(day, moonPhase, monthIndex, beYear) {
        this.day = day;
        this.moonPhase = moonPhase;
        this.monthIndex = monthIndex;
        this.beYear = beYear;
    }
    getDayNumber() {
        if (this.moonPhase === MoonPhase.Waxing) { // កើត
            return this.day - 1; // day 1-15 → dayNum 0-14
        }
        else { // រោច
            return 15 + (this.day - 1); // day 1-15 → dayNum 15-29
        }
    }
    static fromDayNumber(dayNum) {
        if (dayNum < 15) {
            return { day: dayNum + 1, moonPhase: MoonPhase.Waxing }; // dayNum 0-14 → day 1-15
        }
        else {
            return { day: (dayNum - 15) + 1, moonPhase: MoonPhase.Waning }; // dayNum 15-29 → day 1-15
        }
    }
    addDays(count) {
        if (count === 0)
            return this;
        if (count < 0)
            return this.subtractDays(-count);
        let result = new KhmerDate(this.day, this.moonPhase, this.monthIndex, this.beYear);
        let remaining = count;
        while (remaining > 0) {
            const daysInMonth = getNumberOfDaysInKhmerMonth(result.monthIndex, result.beYear);
            const currentDayNum = result.getDayNumber();
            const daysLeftInMonth = (daysInMonth - 1) - currentDayNum;
            if (remaining <= daysLeftInMonth) {
                const newDayNum = currentDayNum + remaining;
                const newDay = KhmerDate.fromDayNumber(newDayNum);
                let newBeYear = result.beYear;
                if (result.monthIndex === MonthIndex.Pisakh) { // ពិសាខ
                    if (result.moonPhase === MoonPhase.Waxing && newDay.moonPhase === MoonPhase.Waning) {
                        newBeYear++;
                    }
                }
                result = new KhmerDate(newDay.day, newDay.moonPhase, result.monthIndex, newBeYear);
                remaining = 0;
            }
            else {
                remaining -= (daysLeftInMonth + 1);
                const nextMonth = nextMonthOf(result.monthIndex, result.beYear);
                const newBeYear = (result.monthIndex === MonthIndex.Cheit) ? result.beYear + 1 : result.beYear;
                result = new KhmerDate(1, MoonPhase.Waxing, nextMonth, newBeYear); // Start at 1កើត
            }
        }
        return result;
    }
    subtractDays(count) {
        if (count === 0)
            return this;
        let result = new KhmerDate(this.day, this.moonPhase, this.monthIndex, this.beYear);
        let remaining = count;
        while (remaining > 0) {
            const currentDayNum = result.getDayNumber();
            if (remaining <= currentDayNum) {
                const newDayNum = currentDayNum - remaining;
                const newDay = KhmerDate.fromDayNumber(newDayNum);
                let newBeYear = result.beYear;
                if (result.monthIndex === MonthIndex.Pisakh) { // ពិសាខ
                    if (result.moonPhase === MoonPhase.Waning && newDay.moonPhase === MoonPhase.Waxing) {
                        newBeYear--;
                    }
                }
                result = new KhmerDate(newDay.day, newDay.moonPhase, result.monthIndex, newBeYear);
                remaining = 0;
            }
            else {
                remaining -= (currentDayNum + 1);
                const prevMonth = previousMonthOf(result.monthIndex, result.beYear);
                const newBeYear = (result.monthIndex === MonthIndex.Pisakh) ? result.beYear - 1 : result.beYear;
                const daysInPrevMonth = getNumberOfDaysInKhmerMonth(prevMonth, newBeYear);
                const newDay = KhmerDate.fromDayNumber(daysInPrevMonth - 1);
                result = new KhmerDate(newDay.day, newDay.moonPhase, prevMonth, newBeYear);
            }
        }
        return result;
    }
    toString() {
        return `${this.day}${MoonPhaseNames[this.moonPhase]} ខែ${LunarMonthNames[this.monthIndex]} ព.ស.${this.beYear}`;
    }
}
function getMaybeBEYear(year, month) {
    if (month <= 4) {
        return year + 543;
    }
    else {
        return year + 544;
    }
}
const visakhaBocheaCache = {};
const newYearInfoCache = {};
function getPisakhaBochea(year, isSearching = false) {
    if (visakhaBocheaCache[year]) {
        return visakhaBocheaCache[year];
    }
    for (let searchMonth = 4; searchMonth <= 6; searchMonth++) {
        const daysInMonth = new Date(year, searchMonth, 0).getDate();
        for (let searchDay = 1; searchDay <= daysInMonth; searchDay++) {
            const result = gregorianToKhmerInternal(year, searchMonth, searchDay, 12, 0, 0, true);
            if (result.khmer.monthIndex === MonthIndex.Pisakh && result._khmerDateObj.getDayNumber() === 15) {
                const timestamp = new Date(year, searchMonth - 1, searchDay, 0, 0, 0, 0).getTime();
                visakhaBocheaCache[year] = timestamp;
                return timestamp;
            }
        }
    }
    const fallback = new Date(year, 3, 15, 0, 0, 0, 0).getTime();
    visakhaBocheaCache[year] = fallback;
    return fallback;
}
function gregorianToKhmerInternal(year, month, day, hour = 0, minute = 0, second = 0, isSearching = false) {
    let epochJdn = gregorianToJulianDay(1900, 1, 1);
    const targetJdn = gregorianToJulianDay(year, month, day);
    let khmerMonth = 1; // បុស្ស
    let khmerDayNumber = 0; // 0-29 format
    let diffDays = targetJdn - epochJdn;
    if (diffDays > 0) {
        while (true) {
            const epochGreg = julianDayToGregorian(epochJdn);
            const nextYearBE = getMaybeBEYear(epochGreg.year + 1, epochGreg.month);
            const daysInNextYear = getNumberOfDaysInKhmerYear(nextYearBE);
            if (diffDays > daysInNextYear) {
                diffDays -= daysInNextYear;
                epochJdn += daysInNextYear;
            }
            else {
                break;
            }
        }
    }
    else if (diffDays < 0) {
        while (diffDays < 0) {
            const epochGreg = julianDayToGregorian(epochJdn);
            const currentYearBE = getMaybeBEYear(epochGreg.year, epochGreg.month);
            const daysInCurrentYear = getNumberOfDaysInKhmerYear(currentYearBE);
            diffDays += daysInCurrentYear;
            epochJdn -= daysInCurrentYear;
        }
    }
    while (diffDays > 0) {
        const epochGreg = julianDayToGregorian(epochJdn);
        const currentBE = getMaybeBEYear(epochGreg.year, epochGreg.month);
        const daysInMonth = getNumberOfDaysInKhmerMonth(khmerMonth, currentBE);
        if (diffDays > daysInMonth) {
            diffDays -= daysInMonth;
            epochJdn += daysInMonth;
            khmerMonth = nextMonthOf(khmerMonth, currentBE);
        }
        else {
            break;
        }
    }
    khmerDayNumber = diffDays;
    const finalBE = getMaybeBEYear(year, month);
    const totalDaysInMonth = getNumberOfDaysInKhmerMonth(khmerMonth, finalBE);
    if (khmerDayNumber >= totalDaysInMonth) {
        khmerDayNumber = khmerDayNumber % totalDaysInMonth;
        khmerMonth = nextMonthOf(khmerMonth, finalBE);
    }
    const khmerDayInfo = KhmerDate.fromDayNumber(khmerDayNumber);
    let beYear;
    if (isSearching) {
        beYear = month <= 4 ? year + 543 : year + 544;
    }
    else {
        const inputTimestamp = new Date(year, month - 1, day, hour, minute, second).getTime();
        const beYearTransitionTimestamp = getPisakhaBochea(year);
        if (inputTimestamp >= beYearTransitionTimestamp) {
            beYear = year + 544;
        }
        else {
            beYear = year + 543;
        }
    }
    let jsYear = beToJs(beYear);
    let animalYearIndex = ((beYear + 4) % 12 + 12) % 12;
    if (!isSearching) {
        const newYearInfo = getNewYearFullInfo(year);
        const inputTimestamp = new Date(year, month - 1, day, hour, minute, second).getTime();
        const visakhaBocheaTimestamp = getPisakhaBochea(year);
        if (inputTimestamp >= newYearInfo.newYearMoment.getTime() && inputTimestamp <= visakhaBocheaTimestamp) {
            animalYearIndex = (animalYearIndex + 1) % 12;
        }
        if (inputTimestamp >= newYearInfo.lerngSakMoment.getTime() && inputTimestamp <= visakhaBocheaTimestamp) {
            jsYear++;
        }
    }
    const sakIndex = ((jsYear % 10) + 10) % 10;
    const dayOfWeek = getDayOfWeek(year, month, day);
    const khmerDate = new KhmerDate(khmerDayInfo.day, khmerDayInfo.moonPhase, khmerMonth, beYear);
    return {
        gregorian: { year, month, day, hour, minute, second, dayOfWeek },
        khmer: {
            day: khmerDayInfo.day,
            moonPhase: khmerDayInfo.moonPhase,
            moonPhaseName: MoonPhaseNames[khmerDayInfo.moonPhase],
            monthIndex: khmerMonth,
            monthName: LunarMonthNames[khmerMonth],
            beYear: beYear,
            jsYear: jsYear,
            animalYear: animalYearIndex,
            animalYearName: AnimalYearNames[animalYearIndex],
            sak: sakIndex,
            sakName: SakNames[sakIndex],
            dayOfWeek: dayOfWeek,
            dayOfWeekName: WeekdayNames[dayOfWeek]
        },
        _khmerDateObj: khmerDate
    };
}
function khmerToGregorian(day, moonPhase, monthIndex, beYear) {
    validateKhmerDate(day, moonPhase, monthIndex, beYear);
    const moonPhaseNum = typeof moonPhase === 'number' ? moonPhase : moonPhase;
    const monthIndexNum = typeof monthIndex === 'number' ? monthIndex : monthIndex;
    const approxYear = beYear - 544;
    const startYear = approxYear - 2;
    const endYear = approxYear + 2;
    let candidates = [];
    for (let year = startYear; year <= endYear; year++) {
        for (let month = 1; month <= 12; month++) {
            const daysInMonth = getDaysInGregorianMonth(year, month);
            for (let gDay = 1; gDay <= daysInMonth; gDay++) {
                const isAroundBEYearChange = monthIndexNum === MonthIndex.Pisakh &&
                    ((day === 15 && moonPhaseNum === MoonPhase.Waxing) || (day === 1 && moonPhaseNum === MoonPhase.Waning));
                const timesToCheck = isAroundBEYearChange
                    ? [0, 6, 12, 18, 23] // Check at different hours
                    : [0]; // Normal case: just check at midnight
                for (const hour of timesToCheck) {
                    const khmerResult = gregorianToKhmerInternal(year, month, gDay, hour, 0, 0, false);
                    if (khmerResult.khmer.beYear === beYear &&
                        khmerResult.khmer.monthIndex === monthIndexNum &&
                        khmerResult.khmer.day === day &&
                        khmerResult.khmer.moonPhase === moonPhaseNum) {
                        candidates.push({ year, month, day: gDay });
                        break; // Found a match for this date, no need to check other times
                    }
                }
            }
        }
    }
    if (candidates.length === 0) {
        throw new Error(`Could not find Gregorian date for Khmer date: ${day} ${moonPhaseNum === MoonPhase.Waxing ? 'កើត' : 'រោច'} month ${monthIndexNum} BE ${beYear}`);
    }
    if (candidates.length > 1) {
        const minDistance = Math.min(...candidates.map(c => Math.abs(c.year - approxYear)));
        const closestCandidates = candidates.filter(c => Math.abs(c.year - approxYear) === minDistance);
        if (closestCandidates.length === 1) {
            return closestCandidates[0];
        }
        const noonMatches = closestCandidates.filter(c => {
            const noonCheck = gregorianToKhmerInternal(c.year, c.month, c.day, 12, 0, 0, false);
            return noonCheck.khmer.beYear === beYear &&
                noonCheck.khmer.monthIndex === monthIndexNum &&
                noonCheck.khmer.day === day &&
                noonCheck.khmer.moonPhase === moonPhaseNum;
        });
        if (noonMatches.length > 0) {
            return noonMatches[0];
        }
        return closestCandidates[0];
    }
    return candidates[0];
}
function getNewYearFullInfo(ceYear) {
    if (newYearInfoCache[ceYear]) {
        return newYearInfoCache[ceYear];
    }
    const jsYear = adToJs(ceYear);
    let newYearInfo = getNewYearInfo(jsYear);
    let bodithey = getBoditheyJs(jsYear);
    const isAthikameasPrev = isAdhikameas(jsYear - 1);
    const isChantrathimeasPrev = isChantrathimeas(jsYear - 1);
    if (isAthikameasPrev && isChantrathimeasPrev) {
        bodithey = (bodithey + 1) % 30;
    }
    const lunarDateLerngSak = {
        day: bodithey >= 6 ? bodithey - 1 : bodithey,
        month: bodithey >= 6 ? 4 : 5 // ចេត្រ or ពិសាខ
    };
    const numberNewYearDay = newYearInfo.newYearsDaySotins[0].angsar === 0 ? 4 : 3;
    const epochLerngSakGreg = { year: ceYear, month: 4, day: 17 };
    const khEpoch = gregorianToKhmerInternal(ceYear, 4, 17, 12, 0, 0, true)._khmerDateObj;
    const diffFromEpoch = ((khEpoch.monthIndex - 4) * 29 + khEpoch.getDayNumber()) -
        ((lunarDateLerngSak.month - 4) * 29 + lunarDateLerngSak.day);
    const daysToSubtract = diffFromEpoch + numberNewYearDay - 1;
    const epochJdn = gregorianToJulianDay(epochLerngSakGreg.year, epochLerngSakGreg.month, epochLerngSakGreg.day);
    let newYearJdn = epochJdn - daysToSubtract;
    if (khNewYearMoments[ceYear]) {
        const [datePart, timePart] = khNewYearMoments[ceYear].split(' ');
        const [d, m, y] = datePart.split('-').map(Number);
        const [hr, min] = timePart.split(':').map(Number);
        newYearInfo.timeOfNewYear = { hour: hr, minute: min };
        newYearJdn = gregorianToJulianDay(y, m, d);
    }
    const newYearDate = julianDayToGregorian(newYearJdn);
    const newYearMoment = new Date(newYearDate.year, newYearDate.month - 1, newYearDate.day, newYearInfo.timeOfNewYear.hour, newYearInfo.timeOfNewYear.minute);
    const lerngSakJdn = newYearJdn + numberNewYearDay - 1;
    const lerngSakDate = julianDayToGregorian(lerngSakJdn);
    const lerngSakMoment = new Date(lerngSakDate.year, lerngSakDate.month - 1, lerngSakDate.day, 0, 0, 0); // Midnight
    const result = {
        newYearMoment,
        lerngSakMoment,
        newYearInfo: {
            year: newYearDate.year,
            month: newYearDate.month,
            day: newYearDate.day,
            hour: newYearInfo.timeOfNewYear.hour,
            minute: newYearInfo.timeOfNewYear.minute
        }
    };
    newYearInfoCache[ceYear] = result;
    return result;
}
function getKhmerNewYear(ceYear) {
    const info = getNewYearFullInfo(ceYear);
    return info.newYearInfo;
}
function formatKhmer(khmerData, formatString) {
    if (!formatString) {
        const { khmer } = khmerData;
        const moonDay = `${khmer.day}${khmer.moonPhaseName}`;
        return toKhmerNumeral(`ថ្ងៃ${khmer.dayOfWeekName} ${moonDay} ខែ${khmer.monthName} ឆ្នាំ${khmer.animalYearName} ${khmer.sakName} ពុទ្ធសករាជ ${khmer.beYear}`);
    }
    const formatRules = {
        'W': () => khmerData.khmer.dayOfWeekName,
        'w': () => WeekdayNamesShort[khmerData.gregorian.dayOfWeek],
        'd': () => toKhmerNumeral(khmerData.khmer.day),
        'D': () => toKhmerNumeral((khmerData.khmer.day < 10 ? '0' : '') + khmerData.khmer.day),
        'dr': () => khmerData.khmer.day,
        'Dr': () => (khmerData.khmer.day < 10 ? '0' : '') + khmerData.khmer.day,
        'ds': () => toKhmerNumeral(khmerData.gregorian.day),
        'Ds': () => toKhmerNumeral((khmerData.gregorian.day < 10 ? '0' : '') + khmerData.gregorian.day),
        'dsr': () => khmerData.gregorian.day,
        'Dsr': () => (khmerData.gregorian.day < 10 ? '0' : '') + khmerData.gregorian.day,
        'n': () => MoonPhaseShort[khmerData.khmer.moonPhase],
        'N': () => khmerData.khmer.moonPhaseName,
        'o': () => MoonDaySymbols[khmerData._khmerDateObj.getDayNumber()],
        'm': () => khmerData.khmer.monthName,
        'M': () => SolarMonthNames[khmerData.gregorian.month - 1],
        'a': () => khmerData.khmer.animalYearName,
        'as': () => AnimalYearEmojis[khmerData.khmer.animalYear],
        'e': () => khmerData.khmer.sakName,
        'b': () => toKhmerNumeral(khmerData.khmer.beYear),
        'br': () => khmerData.khmer.beYear,
        'c': () => toKhmerNumeral(khmerData.gregorian.year),
        'cr': () => khmerData.gregorian.year,
        'j': () => toKhmerNumeral(khmerData.khmer.jsYear),
        'jr': () => khmerData.khmer.jsYear,
        'Ms': () => SolarMonthAbbreviationNames[khmerData.gregorian.month - 1],
        'ms': () => LunarMonthAbbreviationNames[khmerData.khmer.monthIndex]
    };
    const sortedKeys = Object.keys(formatRules).sort((a, b) => b.length - a.length);
    const regex = new RegExp(`\\[([^\\]]+)\\]|(${sortedKeys.join('|')})`, 'g');
    const result = formatString.replace(regex, (match, escaped, token) => {
        if (escaped) {
            return escaped;
        }
        const value = formatRules[token]();
        return String(value);
    });
    return result;
}
function gregorianToKhmer(year, month, day, hour = 0, minute = 0, second = 0) {
    validateGregorianDate(year, month, day, hour, minute, second);
    return gregorianToKhmerInternal(year, month, day, hour, minute, second, false);
}
function fromGregorian(year, month, day, hour = 0, minute = 0, second = 0) {
    return gregorianToKhmer(year, month, day, hour, minute, second);
}
function fromKhmer(day, moonPhase, monthIndex, beYear) {
    return khmerToGregorian(day, moonPhase, monthIndex, beYear);
}
function getNewYear(ceYear) {
    return getKhmerNewYear(ceYear);
}
function format(khmerData, formatString) {
    return formatKhmer(khmerData, formatString);
}
function fromDate(date) {
    validateDateObject(date);
    return gregorianToKhmer(date.getFullYear(), date.getMonth() + 1, date.getDate(), date.getHours(), date.getMinutes(), date.getSeconds());
}
function toDate(day, moonPhase, monthIndex, beYear) {
    const greg = khmerToGregorian(day, moonPhase, monthIndex, beYear);
    return new Date(greg.year, greg.month - 1, greg.day);
}
exports.constants = {
    LunarMonths,
    LunarMonthNames,
    SolarMonthNames,
    SolarMonthAbbreviationNames,
    LunarMonthAbbreviationNames,
    AnimalYearNames,
    AnimalYearEmojis,
    SakNames,
    WeekdayNames,
    MoonPhaseNames
};
exports.default = {
    fromGregorian,
    fromKhmer,
    getNewYear,
    format,
    fromDate,
    toDate,
    constants: exports.constants,
    MoonPhase,
    MonthIndex,
    AnimalYear,
    Sak,
    DayOfWeek
};


  return module.exports;
}));
