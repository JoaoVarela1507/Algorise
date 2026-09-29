import { useNavigate } from 'react-router-dom'
import { OnboardingWizard } from '@/components/onboarding/OnboardingWizard'

export function OnboardingPage() {
  const navigate = useNavigate()

  return <OnboardingWizard onVoltarInicio={() => navigate('/cadastro')} />
}
