import { redirect } from "next/navigation";

/** Root: the dashboard home is the Live Market & Agent page. */
export default function RootPage() {
  redirect("/live-markets");
}
