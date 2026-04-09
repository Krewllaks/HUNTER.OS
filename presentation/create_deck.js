const PptxGenJS = require("C:/Users/bahti/AppData/Roaming/npm/node_modules/pptxgenjs");
const React = require("C:/Users/bahti/AppData/Roaming/npm/node_modules/react");
const ReactDOMServer = require("C:/Users/bahti/AppData/Roaming/npm/node_modules/react-dom/server");
const sharp = require("C:/Users/bahti/AppData/Roaming/npm/node_modules/sharp");

// ─── Icon Rendering ───────────────────────────────────────
function renderIconSvg(pathD, color = "#FFFFFF", size = 256, viewBox = "0 0 24 24") {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="${viewBox}" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${pathD}</svg>`;
}

async function iconToBase64(pathD, color, size = 256, viewBox) {
  const svg = renderIconSvg(pathD, color, size, viewBox);
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

// Lucide icon paths (matching our frontend)
const ICONS = {
  target: '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
  search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
  brain: '<path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z"/><path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z"/><path d="M15 13a4.5 4.5 0 0 1-3-4 4.5 4.5 0 0 1-3 4"/><path d="M17.599 6.5a3 3 0 0 0 .399-1.375"/><path d="M6.003 5.125A3 3 0 0 0 6.401 6.5"/><path d="M3.477 10.896a4 4 0 0 1 .585-.396"/><path d="M19.938 10.5a4 4 0 0 1 .585.396"/><path d="M6 18a4 4 0 0 1-1.967-.516"/><path d="M19.967 17.484A4 4 0 0 1 18 18"/>',
  mail: '<rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>',
  messageCircle: '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/>',
  barChart: '<line x1="12" x2="12" y1="20" y2="10"/><line x1="18" x2="18" y1="20" y2="4"/><line x1="6" x2="6" y1="20" y2="16"/>',
  zap: '<path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"/>',
  shield: '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>',
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  rocket: '<path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 3 0 3 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-3 0-3"/>',
  dollarSign: '<line x1="12" x2="12" y1="2" y2="22"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
  trendingUp: '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  arrowRight: '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
  clock: '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
  eye: '<path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0"/><circle cx="12" cy="12" r="3"/>',
  globe: '<circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/>',
  sparkles: '<path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/><path d="M20 3v4"/><path d="M22 5h-4"/><path d="M4 17v2"/><path d="M5 18H3"/>',
};

// Filled icon helper (for icons that need fill instead of stroke)
function filledIconSvg(pathD, fillColor, size = 256, viewBox = "0 0 24 24") {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="${viewBox}" fill="${fillColor}" stroke="none">${pathD}</svg>`;
}

async function filledIconToBase64(pathD, color, size = 256, viewBox) {
  const svg = filledIconSvg(pathD, color, size, viewBox);
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

// ─── Color Palette ────────────────────────────────────────
const C = {
  bg:        "0F0F23",  // Deep dark navy
  bgCard:    "1A1A2E",  // Card background
  bgLight:   "16213E",  // Lighter card
  orange:    "F97316",  // Primary accent
  orangeD:   "EA580C",  // Darker orange
  white:     "FFFFFF",
  gray:      "94A3B8",  // Muted text
  grayDark:  "475569",
  green:     "22C55E",
  red:       "EF4444",
  blue:      "3B82F6",
  purple:    "8B5CF6",
  cyan:      "06B6D4",
};

// Helper: fresh shadow factory
const cardShadow = () => ({ type: "outer", blur: 8, offset: 2, angle: 135, color: "000000", opacity: 0.3 });

async function createPresentation() {
  const pres = new PptxGenJS();
  pres.layout = "LAYOUT_16x9";
  pres.author = "HUNTER.OS";
  pres.title = "HUNTER.OS — AI-Powered Autonomous Sales Hunter";

  // Pre-render icons
  const icons = {};
  for (const [name, path] of Object.entries(ICONS)) {
    icons[name] = await iconToBase64(path, "#F97316", 256);
    icons[name + "W"] = await iconToBase64(path, "#FFFFFF", 256);
  }

  // ═══════════════════════════════════════════════════════════
  // SLIDE 1 — Cover
  // ═══════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };

    // Decorative gradient circle (top-right)
    s.addShape(pres.shapes.OVAL, {
      x: 7.5, y: -1.5, w: 4, h: 4,
      fill: { color: C.orange, transparency: 85 }
    });
    s.addShape(pres.shapes.OVAL, {
      x: 8, y: -1, w: 3, h: 3,
      fill: { color: C.orange, transparency: 70 }
    });

    // Bottom-left decorative
    s.addShape(pres.shapes.OVAL, {
      x: -1.5, y: 3.5, w: 3.5, h: 3.5,
      fill: { color: C.orange, transparency: 90 }
    });

    // Logo / Brand
    s.addText("HUNTER.OS", {
      x: 0.8, y: 0.5, w: 4, h: 0.7,
      fontSize: 28, fontFace: "Arial Black", color: C.orange, bold: true, margin: 0
    });
    s.addText("PRECISION GROWTH", {
      x: 0.8, y: 1.1, w: 4, h: 0.4,
      fontSize: 11, fontFace: "Arial", color: C.gray, charSpacing: 4, margin: 0
    });

    // Main title
    s.addText("Hiç Uyumayan\nDijital Satış Avcınız", {
      x: 0.8, y: 2.0, w: 7, h: 1.8,
      fontSize: 42, fontFace: "Arial Black", color: C.white, bold: true,
      lineSpacingMultiple: 1.1, margin: 0
    });

    // Subtitle
    s.addText("AI-Powered Autonomous Sales Hunter", {
      x: 0.8, y: 3.8, w: 7, h: 0.5,
      fontSize: 18, fontFace: "Arial", color: C.orange, italic: true, margin: 0
    });

    // Tagline
    s.addText("Maas istemeyen, tatil yapmayan, her saniye kişiye özel satış yapan yapay zeka.", {
      x: 0.8, y: 4.4, w: 7, h: 0.5,
      fontSize: 13, fontFace: "Arial", color: C.gray, margin: 0
    });

    // Version badge
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 0.8, y: 5.0, w: 1.2, h: 0.35,
      fill: { color: C.orange, transparency: 80 }, rectRadius: 0.05
    });
    s.addText("v0.1 BETA", {
      x: 0.8, y: 5.0, w: 1.2, h: 0.35,
      fontSize: 9, fontFace: "Arial", color: C.orange, align: "center", valign: "middle", margin: 0
    });
  }

  // ═══════════════════════════════════════════════════════════
  // SLIDE 2 — Problem
  // ═══════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };

    // Section label
    s.addText("PROBLEM", {
      x: 0.8, y: 0.4, w: 2, h: 0.4,
      fontSize: 11, fontFace: "Arial", color: C.orange, charSpacing: 4, bold: true, margin: 0
    });

    s.addText("Satış Ekibiniz Neden\nYeterli Değil?", {
      x: 0.8, y: 0.8, w: 8, h: 1.2,
      fontSize: 36, fontFace: "Arial Black", color: C.white, bold: true, margin: 0
    });

    // Pain point cards (2x2 grid)
    const pains = [
      { icon: "clock", title: "Manuel Araştırma", desc: "Saatlerce Google'da arama,\nLinkedIn'de gezinme" },
      { icon: "users", title: "Kişiselleştirme Yok", desc: "Herkese aynı şablon mesaj,\ndüşük yanıt oranı" },
      { icon: "eye", title: "Takip Unutuluyor", desc: "Follow-up kaçırılıyor,\nfırsatlar ölüyor" },
      { icon: "dollarSign", title: "Yüksek Maliyet", desc: "SDR maaşı $3,000+/ay,\ndüşük verimlilik" },
    ];

    for (let i = 0; i < 4; i++) {
      const col = i % 2;
      const row = Math.floor(i / 2);
      const x = 0.8 + col * 4.4;
      const y = 2.3 + row * 1.6;
      const p = pains[i];

      // Card bg
      s.addShape(pres.shapes.RECTANGLE, {
        x, y, w: 4.0, h: 1.35,
        fill: { color: C.bgCard },
        shadow: cardShadow()
      });

      // Red left accent
      s.addShape(pres.shapes.RECTANGLE, {
        x, y, w: 0.06, h: 1.35,
        fill: { color: C.red }
      });

      // Icon
      s.addImage({ data: icons[p.icon], x: x + 0.3, y: y + 0.25, w: 0.4, h: 0.4 });

      // Title
      s.addText(p.title, {
        x: x + 0.85, y: y + 0.15, w: 2.8, h: 0.4,
        fontSize: 15, fontFace: "Arial", color: C.white, bold: true, margin: 0
      });

      // Description
      s.addText(p.desc, {
        x: x + 0.85, y: y + 0.55, w: 3.0, h: 0.75,
        fontSize: 10, fontFace: "Arial", color: C.gray, margin: 0
      });
    }
  }

  // ═══════════════════════════════════════════════════════════
  // SLIDE 3 — Solution
  // ═══════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };

    s.addText("ÇÖZÜM", {
      x: 0.8, y: 0.4, w: 2, h: 0.4,
      fontSize: 11, fontFace: "Arial", color: C.orange, charSpacing: 4, bold: true, margin: 0
    });

    s.addText("HUNTER.OS ile Tanışın", {
      x: 0.8, y: 0.8, w: 8, h: 0.8,
      fontSize: 36, fontFace: "Arial Black", color: C.white, bold: true, margin: 0
    });

    s.addText("Tam otonom AI satış avcısı. Siz uyurken müşteri bulan, analiz eden, mesaj yazan sistem.", {
      x: 0.8, y: 1.6, w: 8, h: 0.5,
      fontSize: 14, fontFace: "Arial", color: C.gray, margin: 0
    });

    // Feature cards (horizontal)
    const features = [
      { icon: "sparkles", title: "AI-Powered", desc: "Gemini AI ile akıllı analiz ve kişiselleştirme" },
      { icon: "globe", title: "7/24 Çalışır", desc: "Tatil yok, mola yok. Her saniye avda." },
      { icon: "messageCircle", title: "Kişiye Özel", desc: "Robot yazdığı anlaşılmayan mesajlar üretir" },
      { icon: "zap", title: "Otonom Takip", desc: "Cevap gelene kadar akıllı follow-up" },
    ];

    for (let i = 0; i < 4; i++) {
      const x = 0.4 + i * 2.4;
      const y = 2.4;
      const f = features[i];

      // Card
      s.addShape(pres.shapes.RECTANGLE, {
        x, y, w: 2.2, h: 2.8,
        fill: { color: C.bgCard },
        shadow: cardShadow()
      });

      // Orange top accent
      s.addShape(pres.shapes.RECTANGLE, {
        x, y, w: 2.2, h: 0.05,
        fill: { color: C.orange }
      });

      // Icon circle
      s.addShape(pres.shapes.OVAL, {
        x: x + 0.65, y: y + 0.35, w: 0.85, h: 0.85,
        fill: { color: C.orange, transparency: 80 }
      });
      s.addImage({ data: icons[f.icon], x: x + 0.82, y: y + 0.52, w: 0.5, h: 0.5 });

      // Title
      s.addText(f.title, {
        x: x + 0.1, y: y + 1.4, w: 2.0, h: 0.4,
        fontSize: 14, fontFace: "Arial", color: C.white, bold: true, align: "center", margin: 0
      });

      // Desc
      s.addText(f.desc, {
        x: x + 0.1, y: y + 1.8, w: 2.0, h: 0.85,
        fontSize: 10, fontFace: "Arial", color: C.gray, align: "center", margin: 0
      });
    }
  }

  // ═══════════════════════════════════════════════════════════
  // SLIDE 4 — Step 1: Describe Product
  // ═══════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };

    // Step number badge
    s.addShape(pres.shapes.OVAL, {
      x: 0.8, y: 0.4, w: 0.6, h: 0.6,
      fill: { color: C.orange }
    });
    s.addText("1", {
      x: 0.8, y: 0.4, w: 0.6, h: 0.6,
      fontSize: 22, fontFace: "Arial Black", color: C.white, align: "center", valign: "middle", margin: 0
    });

    s.addText("Ürününüzü Anlatın", {
      x: 1.6, y: 0.4, w: 5, h: 0.6,
      fontSize: 32, fontFace: "Arial Black", color: C.white, bold: true, valign: "middle", margin: 0
    });

    s.addText("Tek yapmanız gereken ürününüzü birkaç cümleyle anlatmak. Gerisini AI halleder.", {
      x: 0.8, y: 1.2, w: 8, h: 0.4,
      fontSize: 13, fontFace: "Arial", color: C.gray, margin: 0
    });

    // Flow diagram: Input → AI Analysis → ICP → Strategies
    const steps = [
      { icon: "mail", label: "Ürün\nTanımı", sub: "Birkaç cümle yeterli" },
      { icon: "brain", label: "AI\nAnaliz", sub: "Gemini 2.0 Flash" },
      { icon: "target", label: "ICP\nProfili", sub: "İdeal müşteri çıkarımı" },
      { icon: "search", label: "Arama\nStratejisi", sub: "Otomatik query'ler" },
    ];

    for (let i = 0; i < 4; i++) {
      const x = 0.6 + i * 2.4;
      const y = 2.1;

      // Card
      s.addShape(pres.shapes.RECTANGLE, {
        x, y, w: 2.0, h: 2.6,
        fill: { color: C.bgCard },
        shadow: cardShadow()
      });

      // Icon
      s.addShape(pres.shapes.OVAL, {
        x: x + 0.6, y: y + 0.3, w: 0.8, h: 0.8,
        fill: { color: C.orange, transparency: 75 }
      });
      s.addImage({ data: icons[steps[i].icon], x: x + 0.75, y: y + 0.45, w: 0.5, h: 0.5 });

      // Label
      s.addText(steps[i].label, {
        x: x + 0.1, y: y + 1.3, w: 1.8, h: 0.6,
        fontSize: 14, fontFace: "Arial", color: C.white, bold: true, align: "center", margin: 0
      });

      // Sub
      s.addText(steps[i].sub, {
        x: x + 0.1, y: y + 1.9, w: 1.8, h: 0.4,
        fontSize: 10, fontFace: "Arial", color: C.gray, align: "center", margin: 0
      });

      // Arrow between cards
      if (i < 3) {
        s.addText("→", {
          x: x + 2.0, y: y + 0.8, w: 0.4, h: 0.5,
          fontSize: 24, fontFace: "Arial", color: C.orange, align: "center", valign: "middle", margin: 0
        });
      }
    }
  }

  // ═══════════════════════════════════════════════════════════
  // SLIDE 5 — Step 2: Autonomous Discovery
  // ═══════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };

    s.addShape(pres.shapes.OVAL, {
      x: 0.8, y: 0.4, w: 0.6, h: 0.6,
      fill: { color: C.orange }
    });
    s.addText("2", {
      x: 0.8, y: 0.4, w: 0.6, h: 0.6,
      fontSize: 22, fontFace: "Arial Black", color: C.white, align: "center", valign: "middle", margin: 0
    });

    s.addText("Otonom Keşif Başlar", {
      x: 1.6, y: 0.4, w: 5, h: 0.6,
      fontSize: 32, fontFace: "Arial Black", color: C.white, bold: true, valign: "middle", margin: 0
    });

    s.addText("AI, Google ve LinkedIn'i tarayarak ideal müşterilerinizi otomatik olarak bulur.", {
      x: 0.8, y: 1.2, w: 8, h: 0.4,
      fontSize: 13, fontFace: "Arial", color: C.gray, margin: 0
    });

    // Left: Process steps
    const processes = [
      { text: "Google Dorking ile hedef sektör taraması", color: C.blue },
      { text: "LinkedIn profil keşfi ve veri çıkarımı", color: C.cyan },
      { text: "Akıllı puanlama (0-100 intent score)", color: C.orange },
      { text: "Triple dedup: email + LinkedIn + domain", color: C.green },
      { text: "Sonuçlar veritabanına kaydedilir", color: C.purple },
    ];

    for (let i = 0; i < processes.length; i++) {
      const y = 1.9 + i * 0.65;
      s.addShape(pres.shapes.RECTANGLE, {
        x: 0.8, y, w: 5.5, h: 0.5,
        fill: { color: C.bgCard }
      });
      // Colored left accent
      s.addShape(pres.shapes.RECTANGLE, {
        x: 0.8, y, w: 0.06, h: 0.5,
        fill: { color: processes[i].color }
      });
      s.addText(`${i + 1}.  ${processes[i].text}`, {
        x: 1.1, y, w: 5.0, h: 0.5,
        fontSize: 13, fontFace: "Arial", color: C.white, valign: "middle", margin: 0
      });
    }

    // Right: Stats card
    s.addShape(pres.shapes.RECTANGLE, {
      x: 6.8, y: 1.9, w: 2.8, h: 3.25,
      fill: { color: C.bgCard },
      shadow: cardShadow()
    });
    s.addText("Performans", {
      x: 6.8, y: 2.05, w: 2.8, h: 0.4,
      fontSize: 14, fontFace: "Arial", color: C.orange, bold: true, align: "center", margin: 0
    });

    const stats = [
      { val: "500+", label: "Lead / gün" },
      { val: "< 5s", label: "Analiz süresi" },
      { val: "%94", label: "Doğruluk oranı" },
    ];

    for (let i = 0; i < stats.length; i++) {
      const y = 2.55 + i * 0.8;
      s.addText(stats[i].val, {
        x: 7.0, y, w: 2.4, h: 0.4,
        fontSize: 28, fontFace: "Arial Black", color: C.white, align: "center", margin: 0
      });
      s.addText(stats[i].label, {
        x: 7.0, y: y + 0.35, w: 2.4, h: 0.3,
        fontSize: 10, fontFace: "Arial", color: C.gray, align: "center", margin: 0
      });
    }
  }

  // ═══════════════════════════════════════════════════════════
  // SLIDE 6 — Step 3: Digital Footprint Analysis
  // ═══════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };

    s.addShape(pres.shapes.OVAL, {
      x: 0.8, y: 0.4, w: 0.6, h: 0.6,
      fill: { color: C.orange }
    });
    s.addText("3", {
      x: 0.8, y: 0.4, w: 0.6, h: 0.6,
      fontSize: 22, fontFace: "Arial Black", color: C.white, align: "center", valign: "middle", margin: 0
    });

    s.addText("Dijital Ayak İzi Analizi", {
      x: 1.6, y: 0.4, w: 5, h: 0.6,
      fontSize: 32, fontFace: "Arial Black", color: C.white, bold: true, valign: "middle", margin: 0
    });

    s.addText("Her lead'in online varlığını derinlemesine analiz ederek 6 katmanlı profil oluşturur.", {
      x: 0.8, y: 1.2, w: 8, h: 0.4,
      fontSize: 13, fontFace: "Arial", color: C.gray, margin: 0
    });

    // 6 Layer cards (3x2)
    const layers = [
      { num: "01", title: "Son Paylaşımlar", desc: "LinkedIn & blog içerikleri" },
      { num: "02", title: "Teknoloji Yığını", desc: "Kullandıkları araçlar" },
      { num: "03", title: "İşe Alım Sinyalleri", desc: "Büyüme & ihtiyaç göstergeleri" },
      { num: "04", title: "Sosyal Etkileşim", desc: "İlgi alanları & network" },
      { num: "05", title: "Zamanlama Analizi", desc: "En uygun temas zamanı" },
      { num: "06", title: "Kişilik Profili", desc: "İletişim tarzı & ortak noktalar" },
    ];

    for (let i = 0; i < 6; i++) {
      const col = i % 3;
      const row = Math.floor(i / 3);
      const x = 0.6 + col * 3.1;
      const y = 1.9 + row * 1.65;
      const l = layers[i];

      s.addShape(pres.shapes.RECTANGLE, {
        x, y, w: 2.8, h: 1.4,
        fill: { color: C.bgCard },
        shadow: cardShadow()
      });

      // Number
      s.addText(l.num, {
        x: x + 0.15, y: y + 0.15, w: 0.6, h: 0.5,
        fontSize: 24, fontFace: "Arial Black", color: C.orange, margin: 0
      });

      // Title
      s.addText(l.title, {
        x: x + 0.7, y: y + 0.2, w: 1.9, h: 0.4,
        fontSize: 13, fontFace: "Arial", color: C.white, bold: true, margin: 0
      });

      // Desc
      s.addText(l.desc, {
        x: x + 0.7, y: y + 0.6, w: 1.9, h: 0.4,
        fontSize: 11, fontFace: "Arial", color: C.gray, margin: 0
      });
    }
  }

  // ═══════════════════════════════════════════════════════════
  // SLIDE 7 — Step 4: Personalized Messages
  // ═══════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };

    s.addShape(pres.shapes.OVAL, {
      x: 0.8, y: 0.4, w: 0.6, h: 0.6,
      fill: { color: C.orange }
    });
    s.addText("4", {
      x: 0.8, y: 0.4, w: 0.6, h: 0.6,
      fontSize: 22, fontFace: "Arial Black", color: C.white, align: "center", valign: "middle", margin: 0
    });

    s.addText("Kişiselleştirilmiş Mesajlar", {
      x: 1.6, y: 0.4, w: 6, h: 0.6,
      fontSize: 32, fontFace: "Arial Black", color: C.white, bold: true, valign: "middle", margin: 0
    });

    // Left column: Message preview mockup
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.6, y: 1.3, w: 4.6, h: 3.8,
      fill: { color: C.bgCard },
      shadow: cardShadow()
    });

    // Email header
    s.addText("✉  Konu: Büyüme stratejiniz hakkında bir fikrim var", {
      x: 0.8, y: 1.45, w: 4.2, h: 0.35,
      fontSize: 11, fontFace: "Arial", color: C.orange, bold: true, margin: 0
    });

    // Divider
    s.addShape(pres.shapes.LINE, {
      x: 0.8, y: 1.85, w: 4.2, h: 0,
      line: { color: C.grayDark, width: 0.5 }
    });

    // Email body
    s.addText(
      "Merhaba Ahmet Bey,\n\n" +
      "LinkedIn'deki \"B2B SaaS için Growth Hacking\" yazınızı\nokudum — özellikle PLG stratejisi konusundaki\nyaklaşımınız çok dikkat çekiciydi.\n\n" +
      "Sizin gibi pazarlama ajanslarının en büyük\nsorununun lead generation olduğunu biliyorum.\nHUNTER.OS tam da bu problemi çözüyor...\n\n" +
      "15 dakikalık bir demo için müsait misiniz?\n\n" +
      "Saygılarımla,\nAli",
      {
        x: 0.8, y: 2.0, w: 4.2, h: 2.8,
        fontSize: 10, fontFace: "Calibri", color: C.gray, margin: 0
      }
    );

    // Arrow annotation
    s.addShape(pres.shapes.LINE, {
      x: 5.4, y: 1.7, w: 0.5, h: 0,
      line: { color: C.orange, width: 1.5 }
    });
    s.addText("Kişiye özel konu satırı", {
      x: 5.9, y: 1.55, w: 3.5, h: 0.3,
      fontSize: 10, fontFace: "Arial", color: C.orange, bold: true, margin: 0
    });

    s.addShape(pres.shapes.LINE, {
      x: 5.4, y: 2.5, w: 0.5, h: 0,
      line: { color: C.orange, width: 1.5 }
    });
    s.addText("Gerçek paylaşımına referans", {
      x: 5.9, y: 2.35, w: 3.5, h: 0.3,
      fontSize: 10, fontFace: "Arial", color: C.orange, bold: true, margin: 0
    });

    s.addShape(pres.shapes.LINE, {
      x: 5.4, y: 3.3, w: 0.5, h: 0,
      line: { color: C.orange, width: 1.5 }
    });
    s.addText("Sektöre özel ağrı noktası", {
      x: 5.9, y: 3.15, w: 3.5, h: 0.3,
      fontSize: 10, fontFace: "Arial", color: C.orange, bold: true, margin: 0
    });

    // Right column: Channels
    const channels = [
      { title: "Email Outreach", desc: "SMTP + tracking pixel ile açılma takibi" },
      { title: "LinkedIn DM", desc: "Bağlantı isteği + kişiselleştirilmiş mesaj" },
      { title: "A/B Testing", desc: "Otomatik varyant testi, kazanan belirleme" },
    ];

    for (let i = 0; i < 3; i++) {
      const y = 3.7 + i * 0.55;
      s.addShape(pres.shapes.RECTANGLE, {
        x: 5.9, y, w: 3.6, h: 0.45,
        fill: { color: C.bgCard }
      });
      s.addShape(pres.shapes.RECTANGLE, {
        x: 5.9, y, w: 0.05, h: 0.45,
        fill: { color: C.orange }
      });
      s.addText([
        { text: channels[i].title + "  ", options: { bold: true, color: C.white, fontSize: 10 } },
        { text: channels[i].desc, options: { color: C.gray, fontSize: 9 } },
      ], {
        x: 6.1, y, w: 3.3, h: 0.45,
        fontFace: "Arial", valign: "middle", margin: 0
      });
    }
  }

  // ═══════════════════════════════════════════════════════════
  // SLIDE 8 — Step 5: Smart Follow-up & Auto-Stop
  // ═══════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };

    s.addShape(pres.shapes.OVAL, {
      x: 0.8, y: 0.4, w: 0.6, h: 0.6,
      fill: { color: C.orange }
    });
    s.addText("5", {
      x: 0.8, y: 0.4, w: 0.6, h: 0.6,
      fontSize: 22, fontFace: "Arial Black", color: C.white, align: "center", valign: "middle", margin: 0
    });

    s.addText("Akıllı Takip & Otomatik Durma", {
      x: 1.6, y: 0.4, w: 6, h: 0.6,
      fontSize: 32, fontFace: "Arial Black", color: C.white, bold: true, valign: "middle", margin: 0
    });

    s.addText("İnsan cevap verdiğinde otomasyon anında durur. Yapay zeka duygu analizi yapar.", {
      x: 0.8, y: 1.2, w: 8, h: 0.4,
      fontSize: 13, fontFace: "Arial", color: C.gray, margin: 0
    });

    // Sentiment analysis cards
    const sentiments = [
      { emoji: "✅", label: "İlgili", desc: "\"Evet, demo görmek isterim\"", color: C.green, action: "→ Toplantı planla" },
      { emoji: "❌", label: "İlgisiz", desc: "\"Şu an ihtiyacımız yok\"", color: C.red, action: "→ 90 gün sonra tekrar" },
      { emoji: "📅", label: "Toplantı", desc: "\"Salı 14:00 uyar\"", color: C.blue, action: "→ Takvime ekle" },
      { emoji: "❓", label: "Soru", desc: "\"Fiyatlar nasıl?\"", color: C.purple, action: "→ Otomatik cevap" },
      { emoji: "🛡️", label: "İtiraz", desc: "\"Bütçemiz sınırlı\"", color: C.orange, action: "→ Objection handling" },
    ];

    for (let i = 0; i < sentiments.length; i++) {
      const y = 1.9 + i * 0.65;
      const sent = sentiments[i];

      s.addShape(pres.shapes.RECTANGLE, {
        x: 0.8, y, w: 8.4, h: 0.55,
        fill: { color: C.bgCard }
      });
      s.addShape(pres.shapes.RECTANGLE, {
        x: 0.8, y, w: 0.06, h: 0.55,
        fill: { color: sent.color }
      });

      s.addText(sent.emoji, {
        x: 1.1, y, w: 0.4, h: 0.55,
        fontSize: 16, valign: "middle", margin: 0
      });

      s.addText(sent.label, {
        x: 1.6, y, w: 1.2, h: 0.55,
        fontSize: 13, fontFace: "Arial", color: C.white, bold: true, valign: "middle", margin: 0
      });

      s.addText(sent.desc, {
        x: 2.8, y, w: 3.5, h: 0.55,
        fontSize: 11, fontFace: "Arial", color: C.gray, italic: true, valign: "middle", margin: 0
      });

      s.addText(sent.action, {
        x: 6.5, y, w: 2.5, h: 0.55,
        fontSize: 11, fontFace: "Arial", color: sent.color, bold: true, valign: "middle", align: "right", margin: 0
      });
    }

    // Bottom highlight
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.8, y: 4.8, w: 8.4, h: 0.55,
      fill: { color: C.orange, transparency: 85 }
    });
    s.addText("⚡  Cevap algılandığında otomasyon anında durur — spam riski sıfır", {
      x: 0.8, y: 4.8, w: 8.4, h: 0.55,
      fontSize: 12, fontFace: "Arial", color: C.orange, bold: true, align: "center", valign: "middle", margin: 0
    });
  }

  // ═══════════════════════════════════════════════════════════
  // SLIDE 9 — Dashboard Preview
  // ═══════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };

    s.addText("KONTROL PANELİ", {
      x: 0.8, y: 0.4, w: 3, h: 0.4,
      fontSize: 11, fontFace: "Arial", color: C.orange, charSpacing: 4, bold: true, margin: 0
    });

    s.addText("Gerçek Zamanlı Hassas Panel", {
      x: 0.8, y: 0.8, w: 8, h: 0.7,
      fontSize: 32, fontFace: "Arial Black", color: C.white, bold: true, margin: 0
    });

    // KPI cards row
    const kpis = [
      { val: "8", label: "Toplam Hedef", color: C.white },
      { val: "0", label: "Aktif Kampanya", color: C.orange },
      { val: "94%", label: "Doğruluk", color: C.green },
      { val: "$12.40", label: "Lead Maliyeti", color: C.cyan },
    ];

    for (let i = 0; i < 4; i++) {
      const x = 0.5 + i * 2.35;
      s.addShape(pres.shapes.RECTANGLE, {
        x, y: 1.7, w: 2.15, h: 1.0,
        fill: { color: C.bgCard },
        shadow: cardShadow()
      });
      s.addText(kpis[i].val, {
        x, y: 1.7, w: 2.15, h: 0.6,
        fontSize: 28, fontFace: "Arial Black", color: kpis[i].color, align: "center", valign: "bottom", margin: 0
      });
      s.addText(kpis[i].label, {
        x, y: 2.35, w: 2.15, h: 0.3,
        fontSize: 10, fontFace: "Arial", color: C.gray, align: "center", margin: 0
      });
    }

    // Funnel row
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: 3.0, w: 5.5, h: 1.3,
      fill: { color: C.bgCard },
      shadow: cardShadow()
    });
    s.addText("DÖNÜŞÜM HUNİSİ", {
      x: 0.7, y: 3.05, w: 3, h: 0.3,
      fontSize: 9, fontFace: "Arial", color: C.gray, charSpacing: 2, margin: 0
    });

    const funnel = [
      { val: "19", label: "Keşif" },
      { val: "9", label: "Araştırma" },
      { val: "482", label: "Ulaşım" },
      { val: "86", label: "Cevap" },
    ];
    for (let i = 0; i < 4; i++) {
      const x = 0.7 + i * 1.3;
      const isLast = i === 3;
      s.addShape(pres.shapes.RECTANGLE, {
        x, y: 3.4, w: 1.1, h: 0.75,
        fill: { color: isLast ? C.orange : C.bgLight }
      });
      s.addText(funnel[i].val, {
        x, y: 3.4, w: 1.1, h: 0.45,
        fontSize: 20, fontFace: "Arial Black", color: C.white, align: "center", valign: "bottom", margin: 0
      });
      s.addText(funnel[i].label, {
        x, y: 3.85, w: 1.1, h: 0.25,
        fontSize: 8, fontFace: "Arial", color: isLast ? C.white : C.gray, align: "center", margin: 0
      });
    }

    // Growth chart card
    s.addShape(pres.shapes.RECTANGLE, {
      x: 6.3, y: 3.0, w: 3.3, h: 2.3,
      fill: { color: C.bgCard },
      shadow: cardShadow()
    });
    s.addText("BÜYÜME ANALİTİĞİ", {
      x: 6.5, y: 3.05, w: 3, h: 0.3,
      fontSize: 9, fontFace: "Arial", color: C.orange, charSpacing: 2, bold: true, margin: 0
    });

    // Mini bar chart simulation
    const bars = [35, 45, 40, 50, 42, 55, 48, 60, 52, 65, 58, 70];
    for (let i = 0; i < bars.length; i++) {
      const bh = bars[i] * 0.025;
      s.addShape(pres.shapes.RECTANGLE, {
        x: 6.55 + i * 0.24, y: 5.0 - bh, w: 0.18, h: bh,
        fill: { color: C.orange, transparency: i < 6 ? 50 : 0 }
      });
    }

    // Hot leads table
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: 4.5, w: 5.5, h: 0.8,
      fill: { color: C.bgCard },
      shadow: cardShadow()
    });
    s.addText("Sıcak Lead'ler & Duygu Analizi", {
      x: 0.7, y: 4.5, w: 3, h: 0.35,
      fontSize: 10, fontFace: "Arial", color: C.white, bold: true, margin: 0
    });
    s.addText("Orcun Uzun  •  Researched  •  INTERESTED", {
      x: 0.7, y: 4.85, w: 5, h: 0.3,
      fontSize: 9, fontFace: "Arial", color: C.gray, margin: 0
    });
  }

  // ═══════════════════════════════════════════════════════════
  // SLIDE 10 — Pricing
  // ═══════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };

    s.addText("FİYATLANDIRMA", {
      x: 0.8, y: 0.3, w: 3, h: 0.4,
      fontSize: 11, fontFace: "Arial", color: C.orange, charSpacing: 4, bold: true, margin: 0
    });

    s.addText("Her Bütçeye Uygun Planlar", {
      x: 0.8, y: 0.7, w: 8, h: 0.7,
      fontSize: 32, fontFace: "Arial Black", color: C.white, bold: true, margin: 0
    });

    const plans = [
      {
        name: "Trial", price: "Ücretsiz", period: "14 gün",
        features: ["10 lead keşfi", "5 kişiselleştirilmiş mesaj", "Temel analitik", "Email kanalı"],
        color: C.gray, highlight: false
      },
      {
        name: "Pro", price: "$49", period: "/ay",
        features: ["Sınırsız lead keşfi", "Sınırsız mesaj", "Email + LinkedIn", "A/B Testing", "Gelişmiş analitik", "Öncelikli destek"],
        color: C.orange, highlight: true
      },
      {
        name: "Enterprise", price: "$149", period: "/ay",
        features: ["Her şey Pro'da olan +", "Çoklu ürün desteği", "Takım yönetimi", "API erişimi", "Özel entegrasyonlar", "Dedicated müşteri temsilcisi"],
        color: C.purple, highlight: false
      },
    ];

    for (let i = 0; i < 3; i++) {
      const x = 0.5 + i * 3.2;
      const p = plans[i];
      const cardH = 4.0;

      // Card
      s.addShape(pres.shapes.RECTANGLE, {
        x, y: 1.5, w: 2.9, h: cardH,
        fill: { color: p.highlight ? C.bgLight : C.bgCard },
        shadow: cardShadow(),
        line: p.highlight ? { color: C.orange, width: 1.5 } : undefined
      });

      // Popular badge
      if (p.highlight) {
        s.addShape(pres.shapes.RECTANGLE, {
          x: x + 0.7, y: 1.35, w: 1.5, h: 0.3,
          fill: { color: C.orange }
        });
        s.addText("EN POPÜLER", {
          x: x + 0.7, y: 1.35, w: 1.5, h: 0.3,
          fontSize: 8, fontFace: "Arial", color: C.white, bold: true, align: "center", valign: "middle", margin: 0
        });
      }

      // Plan name
      s.addText(p.name, {
        x, y: 1.65, w: 2.9, h: 0.4,
        fontSize: 14, fontFace: "Arial", color: p.color, bold: true, align: "center", margin: 0
      });

      // Price
      s.addText(p.price, {
        x, y: 2.0, w: 2.9, h: 0.55,
        fontSize: 36, fontFace: "Arial Black", color: C.white, align: "center", margin: 0
      });
      s.addText(p.period, {
        x, y: 2.5, w: 2.9, h: 0.3,
        fontSize: 11, fontFace: "Arial", color: C.gray, align: "center", margin: 0
      });

      // Divider
      s.addShape(pres.shapes.LINE, {
        x: x + 0.3, y: 2.9, w: 2.3, h: 0,
        line: { color: C.grayDark, width: 0.5 }
      });

      // Features
      const featureItems = p.features.map((f, idx) => ({
        text: "✓  " + f,
        options: {
          breakLine: idx < p.features.length - 1,
          fontSize: 10,
          color: C.gray,
          paraSpaceAfter: 6
        }
      }));

      s.addText(featureItems, {
        x: x + 0.3, y: 3.05, w: 2.4, h: 2.2,
        fontFace: "Arial", margin: 0
      });
    }
  }

  // ═══════════════════════════════════════════════════════════
  // SLIDE 11 — ROI
  // ═══════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };

    s.addText("YATIRIM GETİRİSİ", {
      x: 0.8, y: 0.3, w: 4, h: 0.4,
      fontSize: 11, fontFace: "Arial", color: C.orange, charSpacing: 4, bold: true, margin: 0
    });

    s.addText("Rakamlar Kendisi İçin Konuşuyor", {
      x: 0.8, y: 0.7, w: 8, h: 0.7,
      fontSize: 32, fontFace: "Arial Black", color: C.white, bold: true, margin: 0
    });

    // VS comparison
    // Left: Traditional SDR
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: 1.7, w: 4.3, h: 3.5,
      fill: { color: C.bgCard },
      shadow: cardShadow()
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: 1.7, w: 4.3, h: 0.06,
      fill: { color: C.red }
    });

    s.addText("Geleneksel SDR", {
      x: 0.5, y: 1.85, w: 4.3, h: 0.4,
      fontSize: 16, fontFace: "Arial", color: C.red, bold: true, align: "center", margin: 0
    });

    const oldWay = [
      { label: "Aylık Maliyet", val: "$3,000+", color: C.red },
      { label: "Çalışma Saati", val: "8 saat/gün", color: C.gray },
      { label: "Lead/Gün", val: "15-25", color: C.gray },
      { label: "Kişiselleştirme", val: "Manuel / Şablon", color: C.gray },
      { label: "Takip Başarısı", val: "%40-60", color: C.gray },
    ];

    for (let i = 0; i < oldWay.length; i++) {
      const y = 2.4 + i * 0.5;
      s.addText(oldWay[i].label, {
        x: 0.8, y, w: 2, h: 0.4,
        fontSize: 11, fontFace: "Arial", color: C.gray, margin: 0
      });
      s.addText(oldWay[i].val, {
        x: 2.8, y, w: 1.8, h: 0.4,
        fontSize: 12, fontFace: "Arial", color: oldWay[i].color, bold: true, align: "right", margin: 0
      });
    }

    // VS circle
    s.addShape(pres.shapes.OVAL, {
      x: 4.55, y: 2.95, w: 0.9, h: 0.9,
      fill: { color: C.orange }
    });
    s.addText("VS", {
      x: 4.55, y: 2.95, w: 0.9, h: 0.9,
      fontSize: 18, fontFace: "Arial Black", color: C.white, align: "center", valign: "middle", margin: 0
    });

    // Right: HUNTER.OS
    s.addShape(pres.shapes.RECTANGLE, {
      x: 5.2, y: 1.7, w: 4.3, h: 3.5,
      fill: { color: C.bgCard },
      shadow: cardShadow()
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 5.2, y: 1.7, w: 4.3, h: 0.06,
      fill: { color: C.green }
    });

    s.addText("HUNTER.OS Pro", {
      x: 5.2, y: 1.85, w: 4.3, h: 0.4,
      fontSize: 16, fontFace: "Arial", color: C.green, bold: true, align: "center", margin: 0
    });

    const newWay = [
      { label: "Aylık Maliyet", val: "$49", color: C.green },
      { label: "Çalışma Saati", val: "24/7", color: C.green },
      { label: "Lead/Gün", val: "500+", color: C.green },
      { label: "Kişiselleştirme", val: "AI / 6 Katman", color: C.green },
      { label: "Takip Başarısı", val: "%95+", color: C.green },
    ];

    for (let i = 0; i < newWay.length; i++) {
      const y = 2.4 + i * 0.5;
      s.addText(newWay[i].label, {
        x: 5.5, y, w: 2, h: 0.4,
        fontSize: 11, fontFace: "Arial", color: C.gray, margin: 0
      });
      s.addText(newWay[i].val, {
        x: 7.5, y, w: 1.8, h: 0.4,
        fontSize: 12, fontFace: "Arial", color: newWay[i].color, bold: true, align: "right", margin: 0
      });
    }

    // Bottom highlight: savings
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: 5.0, w: 9, h: 0.45,
      fill: { color: C.orange, transparency: 85 }
    });
    s.addText("💰  %98 maliyet tasarrufu  •  60x daha fazla lead  •  Sıfır tatil/izin/mola", {
      x: 0.5, y: 5.0, w: 9, h: 0.45,
      fontSize: 12, fontFace: "Arial", color: C.orange, bold: true, align: "center", valign: "middle", margin: 0
    });
  }

  // ═══════════════════════════════════════════════════════════
  // SLIDE 12 — CTA / Closing
  // ═══════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };

    // Decorative elements
    s.addShape(pres.shapes.OVAL, {
      x: -1, y: -1, w: 3, h: 3,
      fill: { color: C.orange, transparency: 90 }
    });
    s.addShape(pres.shapes.OVAL, {
      x: 8, y: 3.5, w: 3.5, h: 3.5,
      fill: { color: C.orange, transparency: 88 }
    });

    // Brand
    s.addText("HUNTER.OS", {
      x: 0, y: 1.0, w: 10, h: 0.8,
      fontSize: 48, fontFace: "Arial Black", color: C.orange, bold: true, align: "center", margin: 0
    });

    s.addText("Hemen Başlayın", {
      x: 0, y: 1.8, w: 10, h: 0.7,
      fontSize: 36, fontFace: "Arial Black", color: C.white, bold: true, align: "center", margin: 0
    });

    s.addText("Ücretsiz deneyin. Kredi kartı gerekmez.\n14 gün boyunca tüm özelliklere erişin.", {
      x: 0, y: 2.6, w: 10, h: 0.7,
      fontSize: 15, fontFace: "Arial", color: C.gray, align: "center", margin: 0
    });

    // CTA Button
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 3.5, y: 3.5, w: 3, h: 0.65,
      fill: { color: C.orange },
      rectRadius: 0.1,
      shadow: cardShadow()
    });
    s.addText("Ücretsiz Dene →", {
      x: 3.5, y: 3.5, w: 3, h: 0.65,
      fontSize: 16, fontFace: "Arial", color: C.white, bold: true,
      align: "center", valign: "middle", margin: 0
    });

    // Contact info
    s.addText("hunter.os  •  info@hunter.os", {
      x: 0, y: 4.5, w: 10, h: 0.4,
      fontSize: 12, fontFace: "Arial", color: C.gray, align: "center", margin: 0
    });

    // Bottom tagline
    s.addText("\"Hiç uyumayan, maaş istemeyen ve her saniye kişiye özel satış yapan dijital avci.\"", {
      x: 1, y: 4.9, w: 8, h: 0.4,
      fontSize: 11, fontFace: "Arial", color: C.orange, italic: true, align: "center", margin: 0
    });
  }

  // ─── Save ───────────────────────────────────────────────
  const outPath = "C:/Users/bahti/Desktop/aipoweredsaleshunter/presentation/HUNTER_OS_Sunum.pptx";
  await pres.writeFile({ fileName: outPath });
  console.log("Presentation saved to:", outPath);
}

createPresentation().catch(console.error);
