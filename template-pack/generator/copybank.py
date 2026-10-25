import re
# -*- coding: utf-8 -*-
"""Bilingual copy bank. The ONLY place Khmer text for the template pack is authored.

Every entry: key -> (english, khmer, risk).  risk: low = common phrase, med = ritual term or long sentence
(native review first), high = unsure of idiom. All entries are drafts: review status is 'draft' until a
native reader signs them off in docs/i18n/KHMER-REVIEW-QUEUE.md. Never edit Khmer in the generated files;
edit it here and rebuild.
"""

C = {}

def K(key, en, km, risk="low"):
    assert key not in C, key
    C[key] = {"en": en, "km": km, "risk": risk}

# ---- placeholders (every personal field is a clearly marked placeholder) ----
K("ph.groom", "[Groom name]", "[ឈ្មោះកូនកំលោះ]")
K("ph.bride", "[Bride name]", "[ឈ្មោះកូនក្រមុំ]")
K("ph.name", "[Name]", "[ឈ្មោះ]")
K("ph.host", "[Host name]", "[ឈ្មោះម្ចាស់ពិធី]")
K("ph.date", "[Date]", "[កាលបរិច្ឆេទ]")
K("ph.time", "[Time]", "[ម៉ោង]")
K("ph.venue", "[Venue]", "[ទីកន្លែង]")
K("ph.address", "[Address]", "[អាសយដ្ឋាន]")
K("ph.phone", "[Phone]", "[លេខទូរស័ព្ទ]")
K("ph.age", "[Age]", "[អាយុ]")
K("ph.company", "[Company name]", "[ឈ្មោះក្រុមហ៊ុន]")
K("ph.baby", "[Baby name]", "[ឈ្មោះកូន]")
K("ph.departed", "[Name of the departed]", "[ឈ្មោះអ្នកដែលបានចែកឋាន]", "med")
K("ph.parents_groom", "[Groom's parents]", "[ឪពុកម្តាយកូនកំលោះ]")
K("ph.parents_bride", "[Bride's parents]", "[ឪពុកម្តាយកូនក្រមុំ]")
K("ph.message", "[Your message]", "[សារជូនពររបស់អ្នក]")
K("ph.school", "[School or university]", "[សាលា ឬ សាកលវិទ្យាល័យ]")

# ---- labels ----
K("label.date", "Date", "កាលបរិច្ឆេទ")
K("label.time", "Time", "ម៉ោង")
K("label.venue", "Venue", "ទីកន្លែង")
K("label.location", "Location", "ទីតាំង")
K("label.program", "Programme", "កម្មវិធី")
K("label.dresscode", "Dress code", "ការស្លៀកពាក់")
K("label.contact", "Contact", "ទំនាក់ទំនង")
K("label.map", "Map", "ផែនទី")
K("label.host", "Hosts", "ម្ចាស់ពិធី")
K("label.groom", "Groom", "កូនកំលោះ")
K("label.bride", "Bride", "កូនក្រមុំ")
K("label.son_of", "Son of", "កូនប្រុសរបស់")
K("label.daughter_of", "Daughter of", "កូនស្រីរបស់")
K("label.rsvp", "Kindly confirm your attendance", "សូមបញ្ជាក់ការចូលរួម")
K("label.day1", "Day 1", "ថ្ងៃទី ១")
K("label.day2", "Day 2", "ថ្ងៃទី ២")
K("label.day3", "Day 3", "ថ្ងៃទី ៣")
K("label.morning", "Morning", "ពេលព្រឹក")
K("label.afternoon", "Afternoon", "ពេលរសៀល")
K("label.evening", "Evening", "ពេលល្ងាច")
K("label.dress_traditional", "Traditional Khmer attire", "ស្លៀកពាក់ប្រពៃណីខ្មែរ")
K("label.with_love", "With love and gratitude", "ដោយក្តីស្រឡាញ់ និងការដឹងគុណ", "med")
K("label.with_respect", "With respect, we wish you", "ដោយក្តីគោរព សូមជូនពរ", "med")
K("label.in_memory", "In loving memory", "ក្នុងសេចក្តីនឹករលឹក", "med")
K("label.invited", "You are cordially invited", "សូមគោរពអញ្ជើញ")
K("label.save_the_date", "Save the Date", "សូមកត់ទុកថ្ងៃ", "med")
K("label.hosted_by", "Hosted by", "រៀបចំដោយ")

# ---- schedule items ----
K("sched.welcome", "Welcome of guests", "ពិធីស្វាគមន៍ភ្ញៀវ")
K("sched.chanting", "Monks' blessing chant", "ពិធីសូត្រមន្ត")
K("sched.ancestors", "Offering to ancestors", "ពិធីសែនដូនតា", "med")
K("sched.hair", "Hair-cutting ceremony", "ពិធីកាត់សក់", "med")
K("sched.wrist", "Wrist-tying blessing", "ពិធីចងដៃ", "med")
K("sched.procession", "Gift procession", "ពិធីហែជំនូន", "med")
K("sched.engagement", "Engagement ceremony", "ពិធីភ្ជាប់ពាក្យ")
K("sched.ceremony", "Wedding ceremony", "ពិធីរៀបអាពាហ៍ពិពាហ៍")
K("sched.banquet", "Wedding banquet", "ពិធីជប់លៀង")
K("sched.lunch", "Lunch", "អាហារថ្ងៃត្រង់")
K("sched.dinner", "Dinner", "អាហារពេលល្ងាច")
K("sched.monks_meal", "Chanting and meal offering to the monks", "សូត្រមន្ត និងប្រគេនភត្តាហារដល់ព្រះសង្ឃ", "med")
K("sched.ribbon", "Ribbon-cutting", "ពិធីកាត់ខ្សែបូ")

# ---- wedding ----
K("wedding.title", "Wedding Ceremony", "សិរីមង្គលអាពាហ៍ពិពាហ៍")
K("wedding.invite_formal",
  "Together with their families, request the honour of your presence at the wedding of their son and daughter",
  "សូមគោរពអញ្ជើញ ឯកឧត្តម លោកជំទាវ លោក លោកស្រី អ្នកនាង កញ្ញា ចូលរួមជាភ្ញៀវកិត្តិយស ក្នុងពិធីអាពាហ៍ពិពាហ៍កូនប្រុស និងកូនស្រីរបស់យើងខ្ញុំ", "med")
K("wedding.invite_short",
  "Together with our families, we invite you to celebrate our wedding",
  "សូមគោរពអញ្ជើញលោកអ្នកចូលរួមអបអរសាទរពិធីអាពាហ៍ពិពាហ៍របស់យើងខ្ញុំ", "med")
K("wedding.honour", "Your presence is a great honour to us", "ការចូលរួមរបស់លោកអ្នក គឺជាកិត្តិយសដ៏ខ្ពង់ខ្ពស់សម្រាប់យើងខ្ញុំ", "med")
K("wedding.engagement.title", "Engagement Ceremony", "ពិធីភ្ជាប់ពាក្យ")
K("wedding.engagement.invite", "You are warmly invited to witness our engagement ceremony",
  "សូមគោរពអញ្ជើញលោកអ្នកចូលរួមជាភ្ញៀវកិត្តិយសក្នុងពិធីភ្ជាប់ពាក្យ", "med")
K("wedding.hair.title", "Hair-Cutting Ceremony", "ពិធីកាត់សក់", "med")
K("wedding.hair.invite", "Join us for the traditional blessing before the wedding",
  "សូមគោរពអញ្ជើញចូលរួមពិធីកាត់សក់ តាមប្រពៃណីខ្មែរ មុនពិធីអាពាហ៍ពិពាហ៍", "med")
K("wedding.reception.title", "Wedding Reception", "ពិធីជប់លៀងអាពាហ៍ពិពាហ៍")
K("wedding.reception.invite", "Join us for an evening of dinner and celebration",
  "សូមគោរពអញ្ជើញចូលរួមពិធីជប់លៀងអាហារពេលល្ងាច ដើម្បីអបអរសាទរអាពាហ៍ពិពាហ៍", "med")
K("wedding.program.title", "Three Days of Celebration", "កម្មវិធីអាពាហ៍ពិពាហ៍បីថ្ងៃ", "med")
K("wedding.program.intro", "Please join us for the following ceremonies",
  "សូមគោរពអញ្ជើញចូលរួមក្នុងពិធីដូចខាងក្រោម", "med")

# ---- birthday ----
K("bd.title", "Birthday Celebration", "ពិធីអបអរសាទរខួបកំណើត")
K("bd.happy", "Happy Birthday", "រីករាយថ្ងៃកំណើត")
K("bd.first", "My First Birthday", "ខួបកំណើតគម្រប់ ១ ឆ្នាំ")
K("bd.invite", "You are invited to celebrate the birthday of", "សូមអញ្ជើញចូលរួមអបអរសាទរខួបកំណើតរបស់", "med")
K("bd.kids_invite", "Come and celebrate with us!", "សូមអញ្ជើញមកអបអរសាទរជាមួយយើង!", "med")
K("bd.longevity.title", "Longevity Blessing Ceremony", "ពិធីបុណ្យចម្រើនអាយុ", "med")
K("bd.longevity.invite", "Join us in honouring our elder on this special birthday",
  "សូមគោរពអញ្ជើញចូលរួមពិធីបុណ្យចម្រើនអាយុ", "med")
K("bd.longevity.wish", "May you enjoy a long life and good health", "សូមជូនពរឱ្យមានអាយុយឺនយូរ សុខភាពល្អ", "med")
K("bd.sixty", "60th Birthday", "ខួបកំណើតគម្រប់ ៦០ ឆ្នាំ")

# ---- merit and ceremony ----
K("hw.title", "House Blessing Ceremony", "ពិធីបុណ្យឡើងផ្ទះថ្មី")
K("hw.invite", "We invite you to bless our new home", "សូមគោរពអញ្ជើញចូលរួមពិធីបុណ្យឡើងផ្ទះថ្មីរបស់យើងខ្ញុំ", "med")
K("merit.title", "Merit-Making Ceremony", "ពិធីបុណ្យទាន")
K("merit.invite", "You are invited to join us in making merit", "សូមគោរពអញ្ជើញចូលរួមធ្វើបុណ្យទាន", "med")
K("kathina.title", "Kathina Robe Offering", "បុណ្យកឋិនទាន")
K("kathina.invite", "We invite all benefactors to join the Kathina ceremony", "សូមអញ្ជើញសប្បុរសជនចូលរួមបុណ្យកឋិនទាន", "med")
K("pchum.title", "Pchum Ben", "បុណ្យភ្ជុំបិណ្ឌ")
K("pchum.invite", "In remembrance of our ancestors", "ដើម្បីរំលឹកគុណដូនតា", "med")
K("pchum.line", "You are invited to join the ceremony and dedicate merit to our ancestors",
  "សូមអញ្ជើញចូលរួមបុណ្យភ្ជុំបិណ្ឌ ឧទ្ទិសកុសលជូនដូនតា", "med")
K("memorial.title", "Memorial Ceremony", "ពិធីបុណ្យខួប", "med")
K("memorial.invite", "You are respectfully invited to a ceremony dedicating merit to",
  "សូមគោរពអញ្ជើញចូលរួមពិធីបុណ្យឧទ្ទិសកុសលជូន", "med")
K("memorial.wish", "May the soul rest in peace", "សូមឱ្យវិញ្ញាណក្ខន្ធបានទៅកាន់សុគតិភព", "med")

# ---- greetings and wishes ----
K("ny.title", "Khmer New Year", "បុណ្យចូលឆ្នាំថ្មីប្រពៃណីខ្មែរ")
K("ny.greeting", "Happy Khmer New Year", "សួស្តីឆ្នាំថ្មី")
K("ny.wish", "May the new year bring you health, happiness and prosperity",
  "សូមជូនពរលោកអ្នកប្រកបដោយសុខភាពល្អ សុភមង្គល និងភាពរុងរឿងក្នុងឆ្នាំថ្មី", "med")
K("wf.title", "Water Festival", "បុណ្យអុំទូក")
K("wf.wish", "Wishing you joy and good fortune this Water Festival",
  "សូមជូនពរឱ្យលោកអ្នករីករាយ និងជួបតែសំណាងល្អក្នុងបុណ្យអុំទូក", "med")
K("gny.title", "Happy New Year", "សួស្តីឆ្នាំសកលថ្មី", "med")
K("gny.wish", "Wishing you a bright and joyful year ahead",
  "សូមជូនពរឱ្យលោកអ្នកមានឆ្នាំថ្មីដ៏ភ្លឺស្វាង និងពោរពេញដោយសេចក្តីសុខ", "med")
K("thanks.title", "Thank You", "សូមអរគុណ")
K("thanks.line", "Thank you for celebrating with us", "អរគុណដែលបានចូលរួមអបអរសាទរជាមួយយើងខ្ញុំ", "med")
K("grad.title", "Congratulations, Graduate", "អបអរសាទរបញ្ចប់ការសិក្សា")
K("grad.wish", "Wishing you success in every step ahead",
  "សូមជូនពរឱ្យទទួលបានជោគជ័យគ្រប់ជំហានបន្ទាប់", "med")
K("baby.title", "Welcome, Little One", "សូមស្វាគមន៍សមាជិកថ្មី", "med")
K("baby.line", "A new life, a new joy", "ជីវិតថ្មី សេចក្តីរីករាយថ្មី", "med")
K("symp.title", "With Deepest Sympathy", "សូមចូលរួមរំលែកទុក្ខ")
K("symp.line", "Our thoughts are with you and your family",
  "យើងខ្ញុំសូមរំលែកទុក្ខជាមួយលោកអ្នក និងក្រុមគ្រួសារ", "med")
K("well.title", "Get Well Soon", "សូមឱ្យឆាប់ជាសះស្បើយ")
K("well.line", "Wishing you good health again very soon",
  "សូមជូនពរឱ្យមានសុខភាពល្អឡើងវិញឆាប់ៗ", "med")
K("bless.title", "Blessings and Good Wishes", "សូមជូនពរ")
K("bless.line", "May your life be filled with happiness, health and good fortune",
  "សូមឱ្យជីវិតរបស់លោកអ្នកពោរពេញដោយសុភមង្គល សុខភាពល្អ និងសំណាងល្អ", "med")
K("bless.elder", "May you be blessed with long life, good health, strength and wisdom",
  "សូមឱ្យលោកអ្នកមានអាយុយឺនយូរ សុខភាពល្អ កម្លាំងមាំមួន និងប្រាជ្ញាវាងវៃ", "med")
K("cong.title", "Congratulations", "សូមអបអរសាទរ")

# ---- other events ----
K("open.title", "Grand Opening", "ពិធីសម្ពោធបើកដំណើរការ")
K("open.invite", "You are invited to the grand opening of", "សូមគោរពអញ្ជើញចូលរួមពិធីសម្ពោធបើកដំណើរការ", "med")
K("gala.title", "Annual Gala Dinner", "ពិធីជប់លៀងអាហារពេលល្ងាចប្រចាំឆ្នាំ", "med")
K("gala.invite", "The pleasure of your company is requested",
  "សូមគោរពអញ្ជើញលោកអ្នកចូលរួមជាភ្ញៀវកិត្តិយស", "med")
K("anniv.title", "Wedding Anniversary", "ខួបអាពាហ៍ពិពាហ៍")
K("anniv.invite", "Join us as we celebrate our wedding anniversary",
  "សូមអញ្ជើញចូលរួមអបអរសាទរខួបអាពាហ៍ពិពាហ៍របស់យើងខ្ញុំ", "med")

# ---- Khmer calendar vocabulary (so scripts never type months or digits) ----
CALENDAR = {
    "digits": "០១២៣៤៥៦៧៨៩",
    "months": ["មករា", "កុម្ភៈ", "មីនា", "មេសា", "ឧសភា", "មិថុនា", "កក្កដា", "សីហា", "កញ្ញា", "តុលា", "វិច្ឆិកា", "ធ្នូ"],
    "weekdays": ["ថ្ងៃអាទិត្យ", "ថ្ងៃច័ន្ទ", "ថ្ងៃអង្គារ", "ថ្ងៃពុធ", "ថ្ងៃព្រហស្បតិ៍", "ថ្ងៃសុក្រ", "ថ្ងៃសៅរ៍"],
    "day_word": "ថ្ងៃទី", "month_word": "ខែ", "year_word": "ឆ្នាំ",
}

# ---- vocabulary for template names (event word + style word) ----
EVENT_KM = {
    "wedding": "អាពាហ៍ពិពាហ៍", "engagement": "ភ្ជាប់ពាក្យ", "hair": "កាត់សក់", "reception": "ជប់លៀង",
    "program": "កម្មវិធីបីថ្ងៃ", "birthday": "ខួបកំណើត", "first": "ខួបកំណើតគម្រប់ ១ ឆ្នាំ", "kids": "ជប់លៀងកុមារ",
    "longevity": "ចម្រើនអាយុ", "housewarming": "ឡើងផ្ទះថ្មី", "merit": "បុណ្យទាន", "kathina": "កឋិនទាន",
    "pchum": "ភ្ជុំបិណ្ឌ", "memorial": "បុណ្យខួប", "newyear": "ចូលឆ្នាំថ្មី", "water": "បុណ្យអុំទូក",
    "globalny": "ឆ្នាំសកល", "thanks": "សូមអរគុណ", "graduation": "បញ្ចប់ការសិក្សា", "baby": "កូនកើតថ្មី",
    "sympathy": "រំលែកទុក្ខ", "getwell": "ឆាប់ជាសះស្បើយ", "blessing": "ជូនពរ", "opening": "សម្ពោធ",
    "gala": "ជប់លៀងប្រចាំឆ្នាំ", "anniversary": "ខួបអាពាហ៍ពិពាហ៍", "savedate": "កត់ទុកថ្ងៃ",
}
STYLE_KM = {
    "maroon-gold": "ក្រហមមាស", "ivory-frame": "ស៊ុមក្បាច់ខ្មែរ", "lotus-soft": "ផ្កាឈូកទន់ភ្លន់",
    "midnight-gold": "ខៀវយប់ និងមាស", "temple-gate": "ក្លោងទ្វារប្រាសាទ", "quiet-ivory": "ស្អាតសាមញ្ញ",
    "jade-garden": "សួនបៃតង", "sunrise": "ថ្ងៃរះ", "red-gold": "ក្រហម និងមាស", "blush": "ផ្កាឈូកខ្ចី",
    "dark-plum": "ខ្មៅស្វាយ និងមាស", "photo-modern": "ទំនើប", "festive": "ពណ៌ស្រស់",
    "pastel": "ពណ៌ទន់", "bold": "ពណ៌ដិតដាស់", "gold-black": "ខ្មៅ និងមាស", "saffron": "ពណ៌ទឹកក្រូច",
    "twilight": "ព្រលប់", "mono": "ស្ងប់ស្ងាត់", "sun-gold": "មាសព្រះអាទិត្យ", "river-blue": "ទន្លេខៀវ",
    "navy-gold": "ខៀវចាស់ និងមាស", "sage": "បៃតងខ្ចី", "sunny": "ភ្លឺថ្លា", "rose-gold": "មាសផ្កាឈូក",
    "ribbon": "ខ្សែបូ", "classic": "បែបប្រពៃណី",
}


def add_word_breaks():
    """Insert U+200B between Khmer words (Node Intl.Segmenter, ICU dictionary) so every renderer can wrap Khmer."""
    import json, subprocess
    keys = list(C)
    js = ("const s=JSON.parse(require('fs').readFileSync(0,'utf8'));const g=new Intl.Segmenter('km',{granularity:'word'});"
          "console.log(JSON.stringify(s.map(x=>[...g.segment(x)].map(y=>y.segment))));")
    out = subprocess.run(["node", "-e", js], input=json.dumps([C[k]["km"].replace("\u200b", "") for k in keys]), capture_output=True, text=True, check=True)
    for k, segs in zip(keys, json.loads(out.stdout)):
        res = ""
        for sg in segs:
            if res and re.match(r"[\u1780-\u17ff]", sg) and re.match(r"[\u1780-\u17ff]", res[-1]): res += "\u200b"
            res += sg
        C[k]["km"] = res
