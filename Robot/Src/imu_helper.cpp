/**
  *****************************************************************************
  * @file    imu_helper.cpp
  * @author  Tyler Gamvrelis
  *
  * @defgroup IMU_Helper IMU Helper
  * @addtogroup Helpers
  * @{
  *****************************************************************************
  */




/********************************* Includes **********************************/
#include "dsp.h"
#include "imu_helper.h"




/******************************** File-local *********************************/
namespace{
// Constants
// ----------------------------------------------------------------------------
/**
 * @brief Filter coefficients for angular velocity filter. (11 - 1) / 2 = 5
 *        sample delay
 */
static const float velocityCoefficients[11] =
{
    0.030738841, 0.048424201, 0.083829062, 0.11125669, 0.13424691, 0.14013315,
    0.13424691, 0.11125669, 0.083829062, 0.048424201, 0.030738841
};

/**
 * @brief Number of taps in the velocity filter (equal to number of
 *        coefficients)
 */
static constexpr uint16_t velNumTaps = 11;

/**
 * @brief Number of input samples to be buffered before updating filter
 *        output
 */
static constexpr uint32_t velBlockSize = 1;




// Variables
// ----------------------------------------------------------------------------
/** @brief Angular velocity filters along x-, y-, and z-axes */
static dsp::fir_f32<velNumTaps, velBlockSize> velocityFilters[3];




// Classes and structs
// ----------------------------------------------------------------------------
/** @brief Indexes into the velocityFilters array */
enum class VFilter : uint8_t{
    VX = 0,
    VY = 1,
    VZ = 2
};

} // end anonymous namespace




/********************************* Helpers ***********************************/
namespace Helpers{
// Functions
// ----------------------------------------------------------------------------
void initAngularVelocityFilters(){
    for(auto filter : velocityFilters){
        filter.init(velNumTaps, (float*)velocityCoefficients, velBlockSize);
    }
}

void filterAngularVelocity(IMUStruct& imu){
    velocityFilters[VFilter::VX].update(&imu._x_Gyro, &imu._x_Gyro, 1);
    velocityFilters[VFilter::VY].update(&imu._y_Gyro, &imu._y_Gyro, 1);
    velocityFilters[VFilter::VZ].update(&imu._z_Gyro, &imu._z_Gyro, 1);
}

} // end namespace Helpers

/**
 * @}
 */
/* end - IMU_Helper */
