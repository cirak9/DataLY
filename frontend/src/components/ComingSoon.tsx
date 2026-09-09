import { Link, useParams } from "react-router-dom";

/**
 * حاجز مكان مؤقت لصفحات المرحلة 2 (راجع خطة إعادة البناء) — يثبت إن التوجيه
 * (routing) بين كل الشاشات جاهز، قبل ما نبني كل شاشة فعلياً.
 */
export default function ComingSoon({ title }: { title: string }) {
  const params = useParams();
  return (
    <div style={{ maxWidth: 600, margin: "40px auto", fontFamily: "sans-serif" }}>
      <p>
        <Link to="/stores">← المتاجر</Link>
      </p>
      <h1>{title}</h1>
      <p style={{ color: "#666" }}>هذي الشاشة تُبنى بالمرحلة 2 من الخطة.</p>
      {Object.keys(params).length > 0 && (
        <pre style={{ background: "#f5f5f5", padding: 8 }}>{JSON.stringify(params, null, 2)}</pre>
      )}
    </div>
  );
}
