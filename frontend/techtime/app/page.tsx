import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { MessageSquare, BarChart3, History, Wifi, Zap, Shield } from 'lucide-react'

export default function HomePage() {
  return (
    <div className="min-h-[calc(100vh-56px)] flex flex-col">
      {/* Hero Section */}
      <section className="flex-1 flex items-center justify-center px-4 py-16 bg-gradient-to-b from-background to-muted/30">
        <div className="max-w-4xl mx-auto text-center space-y-8">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-sm font-medium">
              <Zap className="h-4 w-4" />
              AI-Powered Diagnostics
            </div>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight">
              Network Diagnostics{' '}
              <span className="text-primary">Made Simple</span>
            </h1>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Troubleshoot network issues with our intelligent assistant. 
              Get instant diagnosis and step-by-step solutions powered by AI.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/chat">
              <Button size="lg" className="w-full sm:w-auto text-lg px-8">
                <MessageSquare className="h-5 w-5 mr-2" />
                Start Diagnosing
              </Button>
            </Link>
            <Link href="/dashboard">
              <Button size="lg" variant="outline" className="w-full sm:w-auto text-lg px-8">
                <BarChart3 className="h-5 w-5 mr-2" />
                View Dashboard
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16 px-4 border-t">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold mb-4">How It Works</h2>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              Our intelligent system guides you through a systematic diagnostic process,
              testing each layer of your network to identify issues quickly.
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            <Card>
              <CardHeader>
                <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
                  <MessageSquare className="h-6 w-6 text-primary" />
                </div>
                <CardTitle>Describe Your Issue</CardTitle>
                <CardDescription>
                  Tell us about your network problem in plain English. 
                  Our AI understands context and symptoms.
                </CardDescription>
              </CardHeader>
            </Card>

            <Card>
              <CardHeader>
                <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
                  <Wifi className="h-6 w-6 text-primary" />
                </div>
                <CardTitle>Automated Testing</CardTitle>
                <CardDescription>
                  We run diagnostic tests on your network, from physical connections 
                  to DNS resolution, identifying issues at each layer.
                </CardDescription>
              </CardHeader>
            </Card>

            <Card>
              <CardHeader>
                <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
                  <Shield className="h-6 w-6 text-primary" />
                </div>
                <CardTitle>Get Solutions</CardTitle>
                <CardDescription>
                  Receive clear, actionable steps to resolve your issue. 
                  Follow along as we guide you to a working network.
                </CardDescription>
              </CardHeader>
            </Card>
          </div>
        </div>
      </section>

      {/* Quick Links */}
      <section className="py-12 px-4 bg-muted/30 border-t">
        <div className="max-w-6xl mx-auto">
          <div className="grid gap-4 sm:grid-cols-3">
            <Link href="/chat" className="group">
              <Card className="h-full transition-colors hover:border-primary">
                <CardContent className="pt-6">
                  <div className="flex items-center gap-3">
                    <MessageSquare className="h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors" />
                    <div>
                      <h3 className="font-semibold">Chat</h3>
                      <p className="text-sm text-muted-foreground">Start a diagnostic session</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>

            <Link href="/dashboard" className="group">
              <Card className="h-full transition-colors hover:border-primary">
                <CardContent className="pt-6">
                  <div className="flex items-center gap-3">
                    <BarChart3 className="h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors" />
                    <div>
                      <h3 className="font-semibold">Dashboard</h3>
                      <p className="text-sm text-muted-foreground">View analytics & insights</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>

            <Link href="/history" className="group">
              <Card className="h-full transition-colors hover:border-primary">
                <CardContent className="pt-6">
                  <div className="flex items-center gap-3">
                    <History className="h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors" />
                    <div>
                      <h3 className="font-semibold">History</h3>
                      <p className="text-sm text-muted-foreground">Browse past sessions</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}
