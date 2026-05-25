import HomeHero from "@/components/movie/HomeHero";
import Trending from "@/components/movie/Trending";
import TopRated from "@/components/movie/TopRated";
import ContinueWatching from "@/components/ContinueWatching";
import Recommendations from "@/components/Recommendations";

export default function Home() {
  return (
    <main className="bg-black text-white min-h-screen overflow-x-hidden">
      <HomeHero />

      <div className="relative space-y-12 pb-16 px-6 pt-8">
        <section>
          <ContinueWatching />
        </section>

        <section>
          <Recommendations />
        </section>

        <section>
          <Trending />
        </section>

        <section>
          <TopRated />
        </section>
      </div>
    </main>
  );
}