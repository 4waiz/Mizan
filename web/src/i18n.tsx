import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

type Lang = "en" | "ar";

const T: Record<string, { en: string; ar: string }> = {
  app_title: { en: "Mizan - Arrears Rescheduling", ar: "ميزان - إعادة جدولة المتأخرات" },
  subtitle: {
    en: "Sheikh Zayed Housing Programme · MOEI",
    ar: "برنامج الشيخ زايد للإسكان · وزارة الطاقة والبنية التحتية",
  },
  login: { en: "Sign in with UAE PASS", ar: "تسجيل الدخول عبر الهوية الرقمية" },
  beneficiary: { en: "Beneficiary", ar: "المستفيد" },
  officer: { en: "Officer", ar: "الموظف" },
  insight: { en: "Insight", ar: "التحليلات" },
  home: { en: "Home", ar: "الرئيسية" },
  new_request: { en: "New Rescheduling Request", ar: "طلب إعادة جدولة جديد" },
  my_case: { en: "My Case", ar: "حالتي" },
  profile: { en: "Beneficiary Profile", ar: "ملف المستفيد" },
  documents: { en: "Documents", ar: "المستندات" },
  validation: { en: "Validation", ar: "التحقق" },
  recommendation: { en: "Recommendation", ar: "التوصية" },
  status: { en: "Case Status", ar: "حالة الطلب" },
  queue: { en: "Review Queue", ar: "قائمة المراجعة" },
  confidence: { en: "Confidence", ar: "درجة الثقة" },
  risk: { en: "Re-default risk", ar: "مخاطر التعثر" },
  income: { en: "Monthly income", ar: "الدخل الشهري" },
  installment: { en: "Installment", ar: "القسط" },
  arrears: { en: "Arrears", ar: "المتأخرات" },
  approve: { en: "Approve", ar: "اعتماد" },
  override: { en: "Override", ar: "تعديل/تجاوز" },
  reject: { en: "Reject", ar: "رفض" },
  notes: { en: "Decision notes", ar: "ملاحظات القرار" },
  submit: { en: "Submit request", ar: "إرسال الطلب" },
  run: { en: "Run assessment", ar: "تشغيل التقييم" },
  escalation: { en: "Escalation reason", ar: "سبب الإحالة" },
  policy_checks: { en: "Policy checks", ar: "فحوصات السياسة" },
  candidate_plans: { en: "Candidate plans", ar: "الخطط المقترحة" },
  evidence: { en: "Evidence", ar: "الأدلة" },
  audit: { en: "Audit trail", ar: "سجل التدقيق" },
  proactive: { en: "Proactive Alerts", ar: "التنبيهات الاستباقية" },
  replay: { en: "Replay Dashboard", ar: "لوحة الإعادة" },
  language: { en: "Language", ar: "اللغة" },
  high_contrast: { en: "High-contrast mode", ar: "وضع التباين العالي" },
  signed_in_as: { en: "Signed in as", ar: "تم تسجيل الدخول باسم" },
};

const OUTCOME: Record<string, { en: string; ar: string }> = {
  UPDATE_INSTALLMENT: { en: "Update installment", ar: "تعديل القسط" },
  TRANSFER_ARREARS: { en: "Transfer arrears to end", ar: "ترحيل المتأخرات للنهاية" },
  MAINTAIN_INSTALLMENT: { en: "Maintain installment", ar: "الإبقاء على القسط" },
  REQUEST_MORE_INFO: { en: "Request more information", ar: "طلب مزيد من المعلومات" },
  REJECT_ACTIVE_REQUEST: { en: "Reject - active request", ar: "رفض - طلب نشط" },
  REFER_TO_OFFICER: { en: "Refer to officer", ar: "إحالة إلى الموظف" },
};

interface I18nCtx {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (k: string) => string;
  outcome: (code?: string | null) => string;
  hc: boolean;
  setHc: (v: boolean) => void;
}

const Ctx = createContext<I18nCtx>(null as any);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(
    () => (localStorage.getItem("mz_lang") as Lang) || "en",
  );
  const [hc, setHc] = useState<boolean>(() => localStorage.getItem("mz_hc") === "1");

  useEffect(() => {
    localStorage.setItem("mz_lang", lang);
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
    document.documentElement.lang = lang;
  }, [lang]);
  useEffect(() => {
    localStorage.setItem("mz_hc", hc ? "1" : "0");
    document.body.classList.toggle("hc", hc);
  }, [hc]);

  const t = (k: string) => T[k]?.[lang] ?? k;
  const outcome = (code?: string | null) =>
    !code ? "-" : OUTCOME[code]?.[lang] ?? code;

  return (
    <Ctx.Provider value={{ lang, setLang, t, outcome, hc, setHc }}>
      {children}
    </Ctx.Provider>
  );
}

export const useI18n = () => useContext(Ctx);
