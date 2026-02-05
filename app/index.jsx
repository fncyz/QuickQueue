import { View, Text, StyleSheet, Image, TouchableOpacity, ScrollView } from 'react-native'
import { useRouter } from 'expo-router'

const Home = () => {
  const router = useRouter()

  return (
    <ScrollView style={styles.scrollContainer} contentContainerStyle={styles.scrollContent}>
      {/* Header */}
      <View style={styles.header}></View>

      {/* Main Content Area */}
      <View style={styles.mainContent}>
        <View style={styles.logoTitleContainer}>
          {/* Logo */}
          <Image 
            source={require('../assets/images/logo.png')} 
            style={styles.logo}
            resizeMode="contain"
          />
          
          {/* Title */}
          <View style={styles.titleContainer}>
            <Text style={styles.title}>
              <Text style={styles.titleYellow}>Q</Text>
              uick<Text style={styles.titleRed}>Q</Text>ueue
            </Text>
            <Text style={styles.tagline}>
              A Smart Online Appointment and Queue Management System for Baranggays
            </Text>
          </View>
        </View>

        {/* Buttons */}
        <View style={styles.buttonContainer}>
          <TouchableOpacity 
            style={[styles.button, styles.downloadButton]}
            onPress={() => {
              // Add download functionality here
            }}
          >
            <Text style={styles.downloadButtonText}>Download</Text>
          </TouchableOpacity>
          
          <TouchableOpacity 
            style={[styles.button, styles.getStartedButton]}
            onPress={() => {
              router.push('/qq/res_login')
            }}
          >
            <Text style={styles.getStartedButtonText}>Get Started</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Footer */}
      <View style={styles.footer}>
        <Text style={styles.footerText}>
          © Consolatrix College of Toledo City. All rights Reserved.
        </Text>
      </View>
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  scrollContainer: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
  },
  header: {
    backgroundColor: '#1a237e', // Dark navy blue
    height: 60,
    width: '100%',
  },
  mainContent: {
    flex: 1,
    backgroundColor: '#2196F3', // Bright blue
    paddingHorizontal: 20,
    paddingVertical: 40,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 500,
  },
  logoTitleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 40,
    flexWrap: 'wrap',
    justifyContent: 'center',
  },
  logo: {
    width: 200,
    height: 200,
    marginRight: 20,
  },
  titleContainer: {
    flex: 1,
    minWidth: 250,
    alignItems: 'left',
  },
  title: {
    fontSize: 78,
    fontWeight: 'bold',
    color: '#FFFFFF',
    marginBottom: 12,
    textAlign: 'left',
  },
  titleYellow: {
    color: '#FFD700', // Yellow
  },
  titleRed: {
    color: '#FF0000', // Red
  },
  tagline: {
    fontSize: 30,
    color: '#FFFFFF',
    lineHeight: 28,
    textAlign: 'center',
  },
  buttonContainer: {
    flexDirection: 'row',
    gap: 20,
    marginTop: 20,
    flexWrap: 'wrap',
    justifyContent: 'center',
  },
  button: {
    paddingVertical: 16,
    paddingHorizontal: 32,
    borderRadius: 8,
    minWidth: 140,
    alignItems: 'center',
  },
  downloadButton: {
    backgroundColor: '#FF0000', // Red
  },
  downloadButtonText: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: 'bold',
  },
  getStartedButton: {
    backgroundColor: '#FFD700', // Yellow/Gold
  },
  getStartedButtonText: {
    color: '#1e1e61',
    fontSize: 18,
    fontWeight: 'bold',
    textDecorationLine: 'underline',
  },
  footer: {
    backgroundColor: '#1a237e', // Dark navy blue
    paddingVertical: 20,
    width: '100%',
    alignItems: 'center',
  },
  footerText: {
    color: '#FFFFFF',
    fontSize: 14,
  },
})

export default Home