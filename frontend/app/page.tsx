import { redirect } from "next/navigation";

/** Root — redirect to Command Center by default. */
export default function RootPage() {
  redirect("/command-center");
}

