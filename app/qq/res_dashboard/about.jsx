import { ScrollView, View, Text, StyleSheet, Image, TouchableOpacity } from 'react-native'
import { useRouter } from 'expo-router'

const About = () => {
  const router = useRouter()

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Top navigation bar */}
      <View style={styles.navbar}>
        <View style={styles.navLeft}>
          <Image
            source={require('../../../assets/images/qq-logo.png')}
            style={styles.mainLogo}
            resizeMode="contain"
          />
          <Image
            source={require('../../../assets/images/toledo.png')}
            style={styles.partnerLogo}
            resizeMode="contain"
          />
          <Image
            source={require('../../../assets/images/cctc.png')}
            style={styles.partnerLogo}
            resizeMode="contain"
          />
        </View>

        <View style={styles.navLinks}>
          <TouchableOpacity
            activeOpacity={0.7}
            onPress={() => router.push('/qq/res_dashboard/res_index')}
          >
            <Text style={[styles.navLink]}>Home</Text>
          </TouchableOpacity>
          <TouchableOpacity
            activeOpacity={0.7}
            onPress={() => {
              router.push('/qq/res_dashboard/book')
            }}
          >
            <Text style={styles.navLink}>Book Now</Text>
          </TouchableOpacity>
          <TouchableOpacity
            activeOpacity={0.7}
            onPress={() => {
              router.push('/qq/res_dashboard/queue')
            }}
          >
            <Text style={styles.navLink}>Queue Status</Text>
          </TouchableOpacity>
            <Text style={[styles.navLink, styles.navLinkActive]}>About</Text>
        </View>

        <TouchableOpacity
          style={styles.logoutButton}
          onPress={() => router.replace('/qq/res_login')}
        >
          <Text style={styles.logoutText}>Logout</Text>
        </TouchableOpacity>
      </View>
        <View style={styles.aboutContainer}>
        <Text style={styles.aboutTitle}>About Us</Text>

        <Text style={styles.aboutText}>
            Welcome to QQ, a smart digital platform designed to make barangay
            services more accessible and organized. As communities continue to
            grow with technology, QQ aims to improve how residents connect with
            their barangay by providing a convenient and efficient way to book
            appointments and manage queues online.
        </Text>

        <Text style={styles.aboutText}>
            This website is created to reduce waiting time, improve service flow,
            and ensure smoother and more transparent experience for both residents
            and barangay staff anytime and anywhere.
        </Text>

        <Text style={styles.collegeName}>
        Consolatrix College of Toledo City, Inc.
        </Text>

        <Image
        source={require('../../../assets/images/cctc.png')}
        style={styles.collegeLogo}
        />


        {/* Vision & Mission */}
        <View style={styles.vmContainer}>
            <View style={styles.vmBox}>
            <Text style={styles.vmTitle}>Vision</Text>
            <Text style={styles.vmText}>
                Commits to:{"\n"}{"\n"}
                1. Strengthen fraternal charity through God-filled friendship and renewed evangelization.{"\n"}
                2. Facilitate the integral development of the learners towards transformation through current researches, {"\n"}relevant curricular offerings, and responsive community extension services.{"\n"}
                3. Fortify leadership and professional development of stakeholders through continuing education and intensive Augustinian Recollect{"\n"}
                4. Develop a community of Christ-centered Augustinian Recollect stewards who are environmentally caring and global leaders.{"\n"}
                5. Nurture one another in the shared mission for the sustainability of the A.R. schools and the social relevance of programs and services.{"\n"}
            </Text>
            </View> 

            <View style={styles.vmBox}>
            <Text style={styles.vmTitle}>Mission</Text>
            <Text style={styles.vmText1}>
                Consolatrix College envisions a life-giving and innovative education
                ministry committed to transforming community of learners into
                Christ-centered Augustinian recollect stewards.
            </Text>
            </View>
        </View>

        {/* Developers */}
        <Text style={styles.devTitle}>Developers</Text>

        <View style={styles.devGrid}>
            <View style={styles.devCircle} />
            <View style={styles.devCircle} />
            <View style={styles.devCircle} />
            <View style={styles.devCircle} />
        </View>
        </View>

    </ScrollView>
  )
}

export default About;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0B3B91',
  },
  content: {
    paddingBottom: 32,
  },
  navbar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 24,
    paddingVertical: 16,
    backgroundColor: '#FFFFFF',
  },
  navLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  mainLogo: {
    width: 40,
    height: 40,
    borderRadius: 999,
  },
  partnerLogo: {
    width: 40,
    height: 40,
  },
  navLinks: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 24,
  },
  navLink: {
    fontSize: 22,
    color: '#1F2933',
    fontWeight: '500',
  },
  navLinkActive: {
    color: '#FBBF24',
  },
  logoutButton: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 999,
    backgroundColor: '#1F3C88',
  },
  logoutText: {
    color: '#FF4D4D',
    fontSize: 22,
    fontWeight: '700',
  },
  aboutContainer: {
  paddingHorizontal: 32,
  paddingVertical: 40,
  alignItems: 'center',
},

aboutTitle: {
  fontSize: 36,
  fontWeight: '800',
  color: '#FFFFFF',
  marginBottom: 20,
},

aboutText: {
  fontSize: 16,
  color: '#E5E7EB',
  textAlign: 'center',
  lineHeight: 24,
  marginBottom: 16,
  maxWidth: 900,
},

collegeName: {
  fontSize: 22,
  fontWeight: '700',
  color: '#FFFFFF',
  marginTop: 24,
  textAlign: 'center',
},

vmContainer: {
  flexDirection: 'row',
  gap: 40,
  marginTop: 20,
  marginBottom: 40,
},

vmBox: {
  maxWidth: 420,
},

vmTitle: {
  fontSize: 22,
  fontWeight: '700',
  color: '#FFFFFF',
  marginBottom: 10,
  textAlign: 'center',
},

vmText: {
  fontSize: 14,
  color: '#E5E7EB',
  lineHeight: 22,
  textAlign: 'justify',
},
vmText1: {
  fontSize: 14,
  color: '#E5E7EB',
  lineHeight: 22,
  textAlign: 'center',
},

devTitle: {
  fontSize: 28,
  fontWeight: '800',
  color: '#FFFFFF',
  marginBottom: 24,
},

devGrid: {
  flexDirection: 'row',
  flexWrap: 'wrap',
  gap: 40,
  justifyContent: 'center',
  maxWidth: 400,
},

devCircle: {
  width: 120,
  height: 120,
  borderRadius: 60,
  backgroundColor: '#E5E7EB',
},

collegeLogo: {
  width: 350,
  height: 350,
  marginTop: 16,
  resizeMode: 'contain',
},


})