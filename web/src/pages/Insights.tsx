import { useI18n } from "../i18n";
import { Band } from "../components/ui";
import HistoricalInsightsDashboard from "../components/HistoricalInsightsDashboard";

export default function Insights() {
  const { t } = useI18n();
  return (
    <>
      <Band title={t("insights")} subtitle={t("insights_subtitle")} fileRef="INSIGHTS · الذكاء" />
      <p className="lead">{t("insights_lead")}</p>
      <HistoricalInsightsDashboard />
    </>
  );
}
