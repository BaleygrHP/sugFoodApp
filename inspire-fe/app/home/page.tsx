import HomeScreen from "@/components/dashboardUser/HomeScreen";

export default function HomePage() {
  return (
    <main
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        padding: 24,
      }}
    >
      <HomeScreen />
    </main>
  );
}