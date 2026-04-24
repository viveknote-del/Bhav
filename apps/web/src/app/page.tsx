export default function Home() {
  return (
    <main className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold">{{PROJECT_DISPLAY_NAME}}</h1>
        <p className="mt-4 text-gray-600">{{PROJECT_DESCRIPTION}}</p>
      </div>
    </main>
  )
}
