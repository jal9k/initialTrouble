import { Skeleton } from '@/components/ui/skeleton'

export default function ChatLoading() {
  return (
    <div className="flex h-[calc(100vh-56px)]">
      {/* Sidebar skeleton */}
      <div className="hidden md:block w-64 border-r p-4 space-y-4">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-8 w-full" />
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
      
      {/* Chat skeleton */}
      <div className="flex-1 flex flex-col">
        <div className="flex-1 p-4 flex items-center justify-center">
          <div className="text-center space-y-4">
            <Skeleton className="h-8 w-64 mx-auto" />
            <Skeleton className="h-4 w-48 mx-auto" />
            <div className="grid grid-cols-2 gap-2 max-w-md mx-auto mt-8">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          </div>
        </div>
        <div className="border-t p-4">
          <div className="flex gap-2">
            <Skeleton className="flex-1 h-11" />
            <Skeleton className="h-11 w-11" />
          </div>
        </div>
      </div>

      {/* Right panel skeleton */}
      <div className="hidden lg:block w-72 border-l p-4 space-y-4">
        <Skeleton className="h-6 w-32" />
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
        <Skeleton className="h-2 w-full mt-4" />
      </div>
    </div>
  )
}

