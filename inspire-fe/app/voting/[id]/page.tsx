import VotingScreen from "@/components/dashboardUser/VotingScreen";

export default async function VotingPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <VotingScreen roomId={id} />;
}
